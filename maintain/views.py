# claims/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import (
    ApplicantDetailsForm, 
    RespondentDetailsForm, 
    ChildFormSet, 
    ApplicantIncomeAssetsForm,
    FinancialsForm
)
import csv
import io
from datetime import date, datetime
from decimal import Decimal
from .pdf_map import PDF_FIELD_MAP, PDF_CHAR_MAP, PDF_CHILD_MAP

from . import utils # Make sure this import is at the top
from django.http import HttpResponse
from django.shortcuts import redirect
from fillpdf import fillpdfs


# This dictionary maps step names to their corresponding form classes
WIZARD_FORMS = {
    'applicant_details': ApplicantDetailsForm,
    'respondent_details': RespondentDetailsForm,
    'child_details': ChildFormSet,
    'applicant_income_assets': ApplicantIncomeAssetsForm, 
    'financials': FinancialsForm,
}

# This defines the order of the steps
WIZARD_STEPS = list(WIZARD_FORMS.keys())


def make_serializable(data):
    """
    Converts date and decimal objects in form data to strings
    to make them JSON serializable for session storage.
    """
    if isinstance(data, list): # This handles formsets
        for item in data:
            for key, value in item.items():
                if isinstance(value, date):
                    item[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    item[key] = str(value)
        return data
    
    # This handles regular forms
    for key, value in data.items():
        if isinstance(value, date):
            data[key] = value.isoformat()
        elif isinstance(value, Decimal):
            data[key] = str(value)
    return data

def claim_wizard(request):
    wizard_data = request.session.get('wizard_data', {})
    session_step = request.session.get('current_step', WIZARD_STEPS[0])

    # --- NAVIGATION LOGIC ---
    get_step = request.GET.get('step')
    if request.method == 'GET' and get_step in WIZARD_STEPS:
        completed_indices = [WIZARD_STEPS.index(s) for s in wizard_data.keys() if s in WIZARD_STEPS]
        max_completed_index = max(completed_indices) if completed_indices else -1
        
        if WIZARD_STEPS.index(get_step) <= max_completed_index + 1:
            current_step_name = get_step
        else:
            current_step_name = WIZARD_STEPS[max_completed_index + 1] if max_completed_index + 1 < len(WIZARD_STEPS) else session_step
    else:
        current_step_name = session_step
    
    request.session['current_step'] = current_step_name
    
    # --- FORM PROCESSING ---
    if request.method == 'POST':
        form = None 
        submitted_step_name = request.POST.get('form_step', current_step_name)
        FormClass = WIZARD_FORMS.get(submitted_step_name)
        
        is_formset = 'formset' in str(FormClass).lower()
        
        if is_formset:
            form = FormClass(request.POST, prefix=submitted_step_name)
        elif submitted_step_name == 'respondent_details':
            applicant_id = wizard_data.get('applicant_details', {}).get('id_number')
            form = FormClass(request.POST, applicant_id=applicant_id)
        else:
            form = FormClass(request.POST)

        if form.is_valid():
            cleaned_data = form.cleaned_data
            if submitted_step_name == 'child_details':
                # Filter out any empty forms or forms marked for deletion
                cleaned_data = [
                    form_data for form_data in cleaned_data 
                    if form_data and not form_data.get('DELETE')
                ]
            
            if submitted_step_name == 'financials':
                # This is a good place to clean any specific text fields if needed.
                # The 'sdadgasd' was an OCR artifact and won't appear from web entry,
                # but this shows how you would clean it.
                if 'other_contributions_text' in cleaned_data:
                    cleaned_data['other_contributions_text'] = cleaned_data['other_contributions_text'].replace('sdadgasd', '').strip()

            wizard_data[submitted_step_name] = make_serializable(cleaned_data)
            request.session['wizard_data'] = wizard_data

            current_index = WIZARD_STEPS.index(submitted_step_name)
            if current_index + 1 < len(WIZARD_STEPS):
                next_step_name = WIZARD_STEPS[current_index + 1]
                request.session['current_step'] = next_step_name
                return redirect(f"{reverse('wizard_start')}?step={next_step_name}")
            else:
                if 'current_step' in request.session:
                    del request.session['current_step']
                return redirect('summary_page')
        else:
            current_step_name = submitted_step_name
            pass
    
    else: # GET request
        FormClass = WIZARD_FORMS.get(current_step_name)
        is_formset = 'formset' in str(FormClass).lower()
        initial_data = wizard_data.get(current_step_name, {})

        if is_formset:
            form = FormClass(initial=initial_data, prefix=current_step_name)
        else:
            form = FormClass(initial=initial_data)

    # --- PREPARE CONTEXT FOR TEMPLATE ---
    template_name = f'wizard/{current_step_name}.html'
    
    step_display_names = [
        'Applicant', 'Respondent', 'Children', 'Your Finances', 'Claim Details'
    ]
    
    # This creates a list like: 
    # [('applicant_details', 'Applicant', 0), ('respondent_details', 'Respondent', 1), ...]
    # This is much easier for the template to work with.
    nav_steps = []
    for i, step_key in enumerate(WIZARD_STEPS):
        nav_steps.append((step_key, step_display_names[i], i))

    context = {
        'form': form,
        'wizard_data': wizard_data,
        'completed_steps': list(wizard_data.keys()),
        'current_step_name': current_step_name,
        'nav_steps': nav_steps, # Use this new list for navigation
        'current_step_index': WIZARD_STEPS.index(current_step_name)
    }
    
    if hasattr(form, 'management_form'):
        context['management_form'] = form.management_form

    return render(request, template_name, context)


def summary_page(request):
    wizard_data = request.session.get('wizard_data', {})
    # In a real app, you would clear the session data here after use
    # For now, we'll keep it for easy testing
    # request.session.flush() 
    return render(request, 'summary.html', {'wizard_data': wizard_data})

def index(request):
    return render(request, 'landing_page.html')


# In claims/views.py
def download_summary_csv(request):
    """
    Retrieves wizard data from the session and generates a CSV file for download.
    """
    wizard_data = request.session.get('wizard_data', {})

    # If there's no data, redirect the user to the start of the wizard
    if not wizard_data:
        return redirect('wizard_start')

    # Create an in-memory text buffer that the csv module can write to
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Write the header row for the CSV file
    writer.writerow(['Section', 'Question', 'Answer'])

    # A helper function to make section titles more readable
    def format_title(title):
        return title.replace('_', ' ').title()

    # Iterate through all the steps and data stored in the session
    for step_name, step_data in wizard_data.items():
        
        # Handle formsets like 'child_details' which are lists of dictionaries
        if isinstance(step_data, list):
            for i, item_data in enumerate(step_data):
                # e.g., "Child Details 1", "Child Details 2"
                item_title = f"{format_title(step_name)} {i + 1}"
                if isinstance(item_data, dict):
                    for question, answer in item_data.items():
                        writer.writerow([item_title, question, str(answer)])

        # Handle regular form data which is a single dictionary
        elif isinstance(step_data, dict):
            section_title = format_title(step_name)
            for question, answer in step_data.items():
                # Skip the hidden form_step field
                if question == 'form_step':
                    continue
                writer.writerow([section_title, question, str(answer)])

    # Get the complete CSV string from the buffer
    csv_string = buffer.getvalue()

    # Create the HttpResponse object with the correct CSV headers.
    # 'text/csv' tells the browser it's a CSV file.
    # 'Content-Disposition' tells the browser to treat it as an attachment and suggests a filename.
    response = HttpResponse(csv_string, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance_application_summary.csv"'
    
    return response

def generate_pdf(request):
    wizard_data = request.session.get('wizard_data', {})
    if not wizard_data:
        return redirect('wizard_start')

    # --- 1. GATHER ALL DATA FROM SESSION ---
    applicant = wizard_data.get('applicant_details', {})
    respondent = wizard_data.get('respondent_details', {})
    children = wizard_data.get('child_details', [])
    income_assets = wizard_data.get('applicant_income_assets', {})
    financials = wizard_data.get('financials', {})

    final_pdf_data = {}

   
    def get_decimal(data, key):
        return Decimal(str(data.get(key) or '0.00'))

    # --- 2. PREPARE AND CALCULATE INCOME & ASSETS ---
    gross = get_decimal(income_assets, 'gross_salary')
    other_income = get_decimal(income_assets, 'other_income_1')
    total_deductions = sum([
        get_decimal(income_assets, 'tax'),
        get_decimal(income_assets, 'medical_aid'),
        get_decimal(income_assets, 'pension'),
        get_decimal(income_assets, 'other_deductions')
    ])
    nett_salary = gross - total_deductions
    total_income = nett_salary + other_income
    
    total_maintenance_claimed = Decimal('0.00')

    applicant_id_number = applicant.get('id_number')
    applicant_dob_obj = utils.extract_dob_from_id(applicant_id_number)
    
    if not applicant_dob_obj:
        try:
            applicant_dob_obj = date.fromisoformat(applicant.get('date_of_birth', ''))
        except (ValueError, TypeError):
            applicant_dob_obj = None # Ensure it's None if invalid
    
    applicant_dob_iso = applicant_dob_obj.isoformat() if applicant_dob_obj else '----------'
    applicant_age = utils.calculate_age(applicant_dob_obj)

    # We will do the same for the respondent for consistency
    respondent_id_number = respondent.get('id_number')
    respondent_dob_obj = utils.extract_dob_from_id(respondent_id_number)
    if not respondent_dob_obj:
        try:
            respondent_dob_obj = date.fromisoformat(respondent.get('date_of_birth', ''))
        except (ValueError, TypeError):
            respondent_dob_obj = None

    respondent_dob_iso = respondent_dob_obj.isoformat() if respondent_dob_obj else '----------'
    respondent_age = utils.calculate_age(respondent_dob_obj)

    applicant_full_address = applicant.get('residential_address', '')
    if applicant.get('postal_code'):
        applicant_full_address += f", {applicant.get('postal_code')}"
    
    respondent_full_address = respondent.get('home_address', '')
    if respondent.get('postal_code'):
        respondent_full_address += f", {respondent.get('postal_code')}"

    # MODIFIED: Split phone numbers into code and number
    applicant_phone_str = str(applicant.get('contact_phone', '')).replace(' ', '')
    applicant_phone_code = applicant_phone_str[:3]
    applicant_phone_number = applicant_phone_str[3:]

    respondent_phone_str = str(respondent.get('contact_phone', '')).replace(' ', '')
    respondent_phone_code = respondent_phone_str[:3]
    respondent_phone_number = respondent_phone_str[3:]
    logical_data = {
        'applicant_ref_no': "",
        'applicant_name': applicant.get('full_name', ''),
        'applicant_age': applicant_age,
        'applicant_address_1': utils.wrap_text(applicant_full_address, 85)[0], 
        'applicant_phone_code': applicant_phone_code,           
        'applicant_phone_number': applicant_phone_number,       
        'applicant_work_address_1': applicant.get('work_address', ''),
        'applicant_work_phone': applicant.get('work_phone', ''),
        'applicant_police_station': applicant.get('nearest_police_station', ''),
        'respondent_name': respondent.get('full_name', ''),
        'respondent_age': respondent_age,
        'respondent_address_1': utils.wrap_text(respondent_full_address, 85)[0], 
        'respondent_phone_code': respondent_phone_code,          
        'respondent_phone_number': respondent_phone_number,       
        'respondent_work_address_1': respondent.get('work_address', ''),
        'respondent_work_phone': respondent.get('work_phone', ''),
        'reason_liable_1': utils.wrap_text(financials.get('legally_liable_reason', ''), 75)[0],
        'reason_liable_2': utils.wrap_text(financials.get('legally_liable_reason', ''), 75)[1],
        'reason_care_1': utils.wrap_text(financials.get('child_in_care_reason', ''), 65)[0],
        'reason_care_2': utils.wrap_text(financials.get('child_in_care_reason', ''), 5)[1],
        'date_not_supported': financials.get('date_not_supported', ''),
        'first_payment_date': financials.get('first_payment_date', ''),
        'payment_in_favour_of': financials.get('payment_in_favour_of', ''),
        'payment_day': financials.get('payment_day', ''),
        'payment_made_to': financials.get('payment_made_to', ''),
        'other_contributions_1': utils.wrap_text(financials.get('other_contributions_text', ''), 80)[0],
        'other_contributions_2': utils.wrap_text(financials.get('other_contributions_text', ''), 80)[1],
        'asset_fixed_property': f"{get_decimal(income_assets, 'fixed_property'):.2f}",
        'asset_investments': f"{get_decimal(income_assets, 'investments'):.2f}",
        'asset_savings': f"{get_decimal(income_assets, 'savings'):.2f}",
        'asset_shares': f"{get_decimal(income_assets, 'shares'):.2f}",
        'asset_motor_vehicles': f"{get_decimal(income_assets, 'motor_vehicles'):.2f}",
        # Income & Deductions (with calculations)
        'income_gross_salary': f"{gross:.2f}",
        'income_other_1': f"{other_income:.2f}",
        'deduction_tax': f"{get_decimal(income_assets, 'tax'):.2f}",
        'deduction_medical_aid': f"{get_decimal(income_assets, 'medical_aid'):.2f}",
        'deduction_pension': f"{get_decimal(income_assets, 'pension'):.2f}",
        'deduction_other': f"{get_decimal(income_assets, 'other_deductions'):.2f}",
        'income_nett_salary': f"{nett_salary:.2f}",
        'income_total': f"{total_income:.2f}",
    }

    for logical_name, pdf_key in PDF_FIELD_MAP.items():
        value = logical_data.get(logical_name)
        if value and str(value) not in ['0.00', '0']:
            final_pdf_data[pdf_key] = value

    # --- 3. POPULATE CHARACTER-BY-CHARACTER FIELDS ---
    def map_chars(pdf_keys, string_data, length):
        string_data = str(string_data).ljust(length)
        for i, key in enumerate(pdf_keys):
            final_pdf_data[key] = string_data[i]

    applicant_dob_str = applicant_dob_obj.strftime('%d%m%y') if applicant_dob_obj else '------'
    map_chars(PDF_CHAR_MAP['applicant_dob'], applicant_dob_str, 6)
    map_chars(PDF_CHAR_MAP['applicant_id'], applicant.get('id_number', ''), 13)
    
    respondent_dob_str = respondent_dob_obj.strftime('%d%m%y') if respondent_dob_obj else '------'
    map_chars(PDF_CHAR_MAP['respondent_dob'], respondent_dob_str, 6)
    map_chars(PDF_CHAR_MAP['respondent_id'], respondent.get('id_number', ''), 13)

    # --- 4. POPULATE THE CHILDREN TABLE ---
    total_maintenance_claimed = get_decimal(financials, 'total_maintenance_claimed')
    num_children = len(children)
    amount_per_child = total_maintenance_claimed / num_children if num_children > 0 else Decimal('0.00')
    
    for i, child_data in enumerate(children):
        if i < len(PDF_CHILD_MAP):
            map_keys = PDF_CHILD_MAP[i]
            
            # Use the calculated per-child amount
            final_pdf_data[map_keys['amount']] = f"{amount_per_child:.2f}"
            final_pdf_data[map_keys['name']] = child_data.get('full_name', '')
            
            child_dob_str = child_data.get('date_of_birth')
            formatted_dob = date.fromisoformat(child_dob_str).strftime('%d%m%Y') if child_dob_str else '--------'
            map_chars(map_keys['dob'], formatted_dob, 8)

    # Populate the total claim amount field on the PDF
    final_pdf_data[PDF_FIELD_MAP['claim_total']] = f"{total_maintenance_claimed:.2f}"


    # --- 5. POPULATE AND SUM THE EXPENDITURE TABLE ---
    expense_rows = [
        # Logical Name,         Self Field Key in Form,     Child Field Key in Form
        ('lodging',             'self_lodging',             'child_lodging'),
        ('groceries',           'self_groceries',           'child_groceries'),
        ('utilities',           'self_utilities',           'child_utilities'),
        ('rates_taxes',         'self_rates_taxes',         'child_rates_taxes'),
        ('laundry',             'self_laundry',             'child_laundry'),
        ('telephone',           'self_telephone',           'child_telephone'),
        ('clothing',            'self_clothing',            'child_clothing'),
        ('school_uniforms',     None,                       'child_school_uniforms'),
        ('transport_public',    'self_transport_public',    'child_transport_public'),
        ('car_insurance',       'self_car_insurance',       'child_car_insurance'),
        ('car_maintenance',     'self_car_maintenance',     'child_car_maintenance'),
        ('fuel',                'self_fuel',                'child_fuel'),
        ('school_fees',         None,                       'child_school_fees'),
        ('stationery',          None,                       'child_stationery'),
        ('extramural',          None,                       'child_extramural'),
        ('medical',             'self_medical',             'child_medical'),
        ('medication',          'self_medication',          'child_medication'),
        ('entertainment',       'self_entertainment',       'child_entertainment'),
        ('other',               'self_other',               'child_other'),
    ]
    total_self_expenditure = Decimal('0.00')
    total_child_expenditure = Decimal('0.00')

    for logical_name, self_key, child_key in expense_rows:
        self_amount = get_decimal(financials, self_key) if self_key else 0
        child_amount = get_decimal(financials, child_key) if child_key else 0
        row_total = self_amount + child_amount

        # Add amounts to the grand totals
        total_self_expenditure += self_amount
        total_child_expenditure += child_amount

        # Populate PDF fields for this row if values are not zero
        if self_amount > 0:
            pdf_field_key = f'expense_self_{logical_name}'
            if pdf_field_key in PDF_FIELD_MAP:
                final_pdf_data[PDF_FIELD_MAP[pdf_field_key]] = f"{self_amount:.2f}"
        
        if child_amount > 0:
            pdf_field_key = f'expense_child_{logical_name}'
            if pdf_field_key in PDF_FIELD_MAP:
                final_pdf_data[PDF_FIELD_MAP[pdf_field_key]] = f"{child_amount:.2f}"
        
        if row_total > 0:
            pdf_field_key = f'expense_total_{logical_name}'
            if pdf_field_key in PDF_FIELD_MAP:
                final_pdf_data[PDF_FIELD_MAP[pdf_field_key]] = f"{row_total:.2f}"

    final_total_expenditure = total_self_expenditure + total_child_expenditure

    # Populate the total fields in the PDF
    if total_self_expenditure > 0:
        final_pdf_data[PDF_FIELD_MAP['expenditure_total_self_col']] = f"{total_self_expenditure:.2f}"
    if total_child_expenditure > 0:
        final_pdf_data[PDF_FIELD_MAP['expenditure_total_child_col']] = f"{total_child_expenditure:.2f}"
    if final_total_expenditure > 0:
        final_pdf_data[PDF_FIELD_MAP['expenditure_total_final']] = f"{final_total_expenditure:.2f}"
    


    # --- 6. GENERATE THE PDF ---
    input_pdf_path = "J101_E_fillable.pdf"
    output_pdf_path = "filled_form.pdf"
    fillpdfs.write_fillable_pdf(input_pdf_path, output_pdf_path, final_pdf_data, flatten=True)

    with open(output_pdf_path, 'rb') as f:
        pdf_file = f.read()
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="maintenance_application_{applicant.get("full_name", "user")}.pdf"'
    
    #request.session.flush() # Temporarily disabled for easier testing
    return response

def downloads_page(request):
    # This view's only job is to render the new template.
    # It can also be where we generate the supporting docs checklist in the future.
    wizard_data = request.session.get('wizard_data', {})
    # Simple checklist for now, we can make this dynamic later
    supporting_docs = [
        "Your South African ID (Original and a certified copy)",
        "Birth certificate for each child (Certified copies)",
        "Your last 3 months of bank statements",
        "Proof of your income (e.g., latest payslip)",
        "Proof of your current residential address",
        "A detailed list of your monthly expenses",
        "(If applicable) Your marriage certificate or divorce order",
        "(If applicable) Any previous maintenance orders",
    ]
    context = {
        'supporting_docs': supporting_docs
    }
    return render(request, 'downloads.html', context)

def dev_autofill_and_redirect(request):
    """
    FOR DEVELOPMENT ONLY.
    Populates the session with sample data and redirects to the summary page
    to allow for rapid testing of the PDF generation step.
    """
    dummy_wizard_data = {
        'applicant_details': {
            'full_name': 'Mary Applicant',
            'id_number': '8501155180085',
            'date_of_birth': '1985-01-15',
            'residential_address': '123 Sample Street, Suburbville',
            'postal_code': '7925',
            'work_address': '456 Business Park, Century City',
            'contact_phone': '0821234567',
            'nearest_police_station': 'Cape Town Central',
        },
        'respondent_details': {
            'full_name': 'John Respondent',
            'id_number': '8203205190087',
            'date_of_birth': '1982-03-20',
            'home_address': '789 Other Road, Othertown',
            'postal_code': '8001',
            'work_address': '101 Industrial Way, Epping',
            'contact_phone': '0739876543',
        },
        'child_details': [
            # NOTE: maintenance_amount is removed, as it will be calculated
            # from the total child expenses.
            {'full_name': 'Thabo Junior Applicant', 'date_of_birth': '2015-06-10', 'DELETE': False},
            {'full_name': 'Jane Applicant', 'date_of_birth': '2018-11-22', 'DELETE': False}
        ],
        'applicant_income_assets': {
            # Assets
            'fixed_property': '1200000.00',
            'investments': '50000.00',
            'savings': '15000.00',
            'shares': '0.00',
            'motor_vehicles': '85000.00',
            # Income
            'gross_salary': '25000.00',
            'other_income_1': '500.00', # The new "Other Income" field
            # Deductions
            'tax': '4500.00',
            'medical_aid': '1800.00',
            'pension': '2000.00',
            'other_deductions': '150.00',
        },
        'financials': {
            # Page 2 Details
            'legally_liable_reason': 'He is the biological father of both children and is legally required to contribute towards their upbringing.',
            'child_in_care_reason': 'The children have lived with me exclusively since their respective births. I am their primary caregiver.',
            'date_not_supported': '2024-01-01',
            'payment_day': '1',
            'payment_made_to': 'The Applicant, M. Applicant',
            'other_contributions_text': '50% of school fees and any medical expenses not covered by the medical aid.',
            # Page 3/4 Expenses (Self and Child breakdown)
            'self_lodging': '4000.00',         'child_lodging': '4000.00',
            'self_groceries': '2000.00',       'child_groceries': '2500.00',
            'self_utilities': '800.00',        'child_utilities': '800.00',
            'self_rates_taxes': '400.00',      'child_rates_taxes': '400.00',
            'self_laundry': '150.00',          'child_laundry': '150.00',
            'self_telephone': '300.00',        'child_telephone': '100.00',
            'self_clothing': '500.00',         'child_clothing': '800.00',
                                               'child_school_uniforms': '1200.00',
            'self_transport_public': '0.00',   'child_transport_public': '450.00',
            'self_fuel': '1000.00',            'child_fuel': '500.00',
            'self_car_maintenance': '250.00',  'child_car_maintenance': '250.00',
            'self_car_insurance': '700.00',    'child_car_insurance': '300.00',
                                               'child_school_fees': '3000.00',
                                               'child_stationery': '350.00',
                                               'child_extramural': '750.00',
            'self_medical': '200.00',          'child_medical': '400.00',
            'self_medication': '100.00',       'child_medication': '150.00',
            'self_entertainment': '400.00',    'child_entertainment': '500.00',
            'self_other': '0.00',              'child_other': '0.00',
        }
    }

    request.session['wizard_data'] = dummy_wizard_data
    return redirect('summary_page')