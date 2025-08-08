from fillpdf import fillpdfs

# This function returns a dictionary of the fields
form_fields = fillpdfs.get_form_fields("J101_E_MANUAL_MAPPING.pdf")

# Print the fields to the console so you can see them
import json
print(json.dumps(form_fields, indent=4))