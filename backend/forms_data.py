# Mock Data for Forms Module
# In a real app, this would be in the database.

FORMS_DB = [
    {
        "id": 1,
        "title": "Rental Agreement Template",
        "category": "Property",
        "description": "Standard residential rental agreement format for 11 months.",
        "language": "English/Hindi",
        "url": "#" 
    },
    {
        "id": 2,
        "title": "RTI Application Form (Form A)",
        "category": "Civil Rights",
        "description": "Application for seeking information under the Right to Information Act, 2005.",
        "language": "English",
        "url": "#"
    },
    {
        "id": 3,
        "title": "FIR Application Format",
        "category": "Criminal",
        "description": "Sample application letter to Station House Officer (SHO) for filing an FIR.",
        "language": "English/Hindi",
        "url": "#"
    },
    {
        "id": 4,
        "title": "Consumer Complaint Form",
        "category": "Consumer",
        "description": "Format for filing a complaint in the District Consumer Forum.",
        "language": "English",
        "url": "#"
    },
    {
        "id": 5,
        "title": "Affidavit for Name Change",
        "category": "General",
        "description": "Standard affidavit format required for changing one's name officially.",
        "language": "English",
        "url": "#"
    },
    {
        "id": 6,
        "title": "Divorce Petition (Mutual Consent)",
        "category": "Family",
        "description": "Draft petition for divorce by mutual consent under Hindu Marriage Act.",
        "language": "English",
        "url": "#"
    }
]

def get_forms(query: str = None):
    if not query:
        return FORMS_DB
    
    query = query.lower()
    return [
        f for f in FORMS_DB 
        if query in f['title'].lower() or query in f['category'].lower()
    ]
