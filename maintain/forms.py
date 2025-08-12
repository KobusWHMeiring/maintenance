from django import forms
from django.forms import formset_factory
from datetime import date
from .utils import extract_dob_from_id

class ApplicantDetailsForm(forms.Form):
    full_name = forms.CharField(
        label="What is your full name?",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    id_number = forms.CharField(
        label="What is your South African ID number?",
        max_length=13,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    residential_address = forms.CharField(
        label="What is your current residential address?",
        help_text="e.g., 123 Sample Street, Suburbville, Cape Town",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    postal_code = forms.CharField(
        label="Postal Code",
        max_length=4,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    work_address = forms.CharField(
        label="What is your work address?",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    contact_phone = forms.CharField(
        label="What is your best contact phone number?",
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    work_phone = forms.CharField(
        label="What is your work phone number (if different)?",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nearest_police_station = forms.CharField(
        label="What is the nearest police station to you?",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    form_step = forms.CharField(widget=forms.HiddenInput(), initial='applicant_details')

    def clean(self):
        cleaned_data = super().clean()
        id_number = cleaned_data.get("id_number")
        date_of_birth = cleaned_data.get("date_of_birth")
        if id_number and date_of_birth:
            dob_from_id = extract_dob_from_id(id_number)
            if dob_from_id and dob_from_id != date_of_birth:
                self.add_error('date_of_birth', "The date of birth does not match the date of birth in the provided ID number. Please check both fields.")
        return cleaned_data

class RespondentDetailsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.applicant_id = kwargs.pop('applicant_id', None)
        super().__init__(*args, **kwargs)

    full_name = forms.CharField(
        label="What is the full name of the other parent (the 'defendant')?",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    id_number = forms.CharField(
        label="What is their ID number (if you know it)?",
        max_length=13,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
    label="What is their date of birth (if you know it)?",
    required=False,
    widget=forms.DateInput(attrs={
        'class': 'form-control form-control--has-icon-right',
        'placeholder': 'YYYY-MM-DD',
        'type': 'date',
        'onclick': 'this.showPicker()' 
    })
)
    home_address = forms.CharField(
        label="What is their home address?",
        help_text="A court official may need to deliver ('serve') documents here. Be as accurate as possible.",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    postal_code = forms.CharField(
        label="Postal Code",
        max_length=4,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    work_address = forms.CharField(
        label="What is their work address (if known)?",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    contact_phone = forms.CharField(
        label="What is their phone number (if known)?",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    work_phone = forms.CharField(
        label="What is their work phone number (if known)?",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    form_step = forms.CharField(widget=forms.HiddenInput(), initial='respondent_details')

    def clean(self):
        cleaned_data = super().clean()
        respondent_id = cleaned_data.get('id_number')
        if self.applicant_id and respondent_id and self.applicant_id == respondent_id:
            self.add_error('id_number', "The respondent's ID number cannot be the same as the applicant's ID number.")
        return cleaned_data

class ChildForm(forms.Form):
    full_name = forms.CharField(
        label="Child's full name",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
        label="Child's date of birth",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'onclick': 'this.showPicker()'})
    )

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError("A child's date of birth cannot be in the future. Please enter a valid date.")
        return dob

ChildFormSet = formset_factory(ChildForm, extra=1, can_delete=True)

class ApplicantIncomeAssetsForm(forms.Form):
    
    currency_attrs = {'class': 'form-control', 'placeholder': '0.00', 'type': 'number', 'step': '0.01'}

    # ASSETS
    fixed_property = forms.DecimalField(label="Value of Fixed Property (e.g., house)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    investments = forms.DecimalField(label="Value of Investments (e.g., unit trusts)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    savings = forms.DecimalField(label="Value of Savings", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    shares = forms.DecimalField(label="Value of Shares", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    motor_vehicles = forms.DecimalField(label="Value of Motor Vehicle(s)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))

    # INCOME
    gross_salary = forms.DecimalField(label="Your Monthly Gross Salary (before deductions)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    other_income_1 = forms.DecimalField(label="Other Monthly Income (if any)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))

    # DEDUCTIONS
    tax = forms.DecimalField(label="Monthly Tax Deduction", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    medical_aid = forms.DecimalField(label="Monthly Medical Aid Deduction", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    pension = forms.DecimalField(label="Monthly Pension/Provident Fund Deduction", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    other_deductions = forms.DecimalField(label="Other Monthly Deductions", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))

    form_step = forms.CharField(widget=forms.HiddenInput(), initial='applicant_income_assets')


    
class FinancialsForm(forms.Form):
    # Common widget attributes for various field types
    currency_attrs = {'class': 'form-control', 'placeholder': '0.00', 'type': 'number', 'step': '0.01'}
    text_area_attrs = {'class': 'form-control', 'rows': 3}
    text_input_attrs = {'class': 'form-control'}
    date_attrs = {'class': 'form-control', 'type': 'date', 'onclick': 'this.showPicker()'}
    day_attrs = {'class': 'form-control', 'type': 'number', 'min': '1', 'max': '31'}

    # CLAIM DETAILS
    legally_liable_reason = forms.CharField(label="Why is the other parent legally required to maintain the child(ren)?", widget=forms.Textarea(attrs=text_area_attrs), help_text="e.g., 'He is the biological father.'")
    child_in_care_reason = forms.CharField(label="Why are the children under your care?", widget=forms.Textarea(attrs=text_area_attrs), help_text="e.g., 'The children have lived with me exclusively since birth.'")
    date_not_supported = forms.DateField(label="Since what date has the defendant not supported the child(ren)?", widget=forms.DateInput(attrs=date_attrs, ), required=False)
    payment_day = forms.IntegerField(label="Payment day of the month?", widget=forms.NumberInput(attrs=day_attrs), required=False)
    payment_made_to = forms.CharField(label="Who should the payment be made to?", widget=forms.TextInput(attrs=text_input_attrs), required=False, help_text="e.g., Your bank account details.")
    other_contributions_text = forms.CharField(label="Other requested contributions?", widget=forms.Textarea(attrs=text_area_attrs), required=False, help_text="e.g., '50% of school fees and uncovered medical expenses.'")
    
    # EXPENSE FIELDS
    self_lodging = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_lodging = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_groceries = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_groceries = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_utilities = forms.DecimalField(label="Your Share (Water/Elec)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_utilities = forms.DecimalField(label="Child(ren)'s Share (Water/Elec)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_rates_taxes = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_rates_taxes = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_laundry = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_laundry = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_telephone = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_telephone = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_clothing = forms.DecimalField(label="Your Share (Clothes/Shoes)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_clothing = forms.DecimalField(label="Child(ren)'s Share (Clothes/Shoes)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_school_uniforms = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_sports_clothes = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_transport_public = forms.DecimalField(label="Your Share (Bus/Taxi)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_transport_public = forms.DecimalField(label="Child(ren)'s Share (Bus/Taxi)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_car_fuel = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_car_fuel = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_car_maintenance = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_car_maintenance = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_car_insurance = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_car_insurance = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_school_fees = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_stationery = forms.DecimalField(label="Child(ren)'s Share (Books/Stationery)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_extramural = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_medical_uncovered = forms.DecimalField(label="Your Share (Doctor/Dentist)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_medical_uncovered = forms.DecimalField(label="Child(ren)'s Share (Doctor/Dentist)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_medication_uncovered = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_medication_uncovered = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_entertainment = forms.DecimalField(label="Your Share (Holidays/Entertainment)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_entertainment = forms.DecimalField(label="Child(ren)'s Share (Holidays/Entertainment)", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    self_other = forms.DecimalField(label="Your Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    child_other = forms.DecimalField(label="Child(ren)'s Share", required=False, decimal_places=2, widget=forms.NumberInput(attrs=currency_attrs))
    
    # FINAL CLAIM
    total_maintenance_claimed = forms.DecimalField(
        label="Total Monthly Maintenance You Are Claiming (R)",
        min_value=0,
        decimal_places=2,
        help_text="Based on the expenses above, enter the total amount you are asking the other parent to contribute.",
        widget=forms.NumberInput(attrs=currency_attrs)
    )
    form_step = forms.CharField(widget=forms.HiddenInput(), initial='financials')