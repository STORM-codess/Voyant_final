from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.template import Template, TemplateQuestion
import uuid

TEMPLATES = [
    {
        "name": "Weekend Trip",
        "description": "Perfect for short getaways with friends",
        "icon": "🏖️",
        "is_custom": False,
        "questions": [
            {
                "question_text": "What is your budget per day?",
                "question_type": "single_choice",
                "options": ["Under ₹500", "₹500-1000", "₹1000-2000", "₹2000-5000", "Above ₹5000"],
                "is_required": True,
                "order": 1,
                "placeholder": None
            },
            {
                "question_text": "What vibe are you looking for?",
                "question_type": "multiple_choice",
                "options": ["Adventure", "Relaxing", "Cultural", "Party", "Nature", "Spiritual"],
                "is_required": True,
                "order": 2,
                "placeholder": None
            },
            {
                "question_text": "How do you prefer to travel?",
                "question_type": "multiple_choice",
                "options": ["Flight", "Train", "Bus", "Road trip", "No preference"],
                "is_required": True,
                "order": 3,
                "placeholder": None
            },
            {
                "question_text": "How many days can you take off?",
                "question_type": "single_choice",
                "options": ["1-2 days", "3-4 days", "5-7 days", "More than a week"],
                "is_required": True,
                "order": 4,
                "placeholder": None
            },
            {
                "question_text": "Places you have already visited?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 5,
                "placeholder": "eg. Goa, Manali, Jaipur"
            },
            {
                "question_text": "Any places you want to avoid?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 6,
                "placeholder": "eg. too hot places, hill stations"
            },
            {
                "question_text": "What is your food preference?",
                "question_type": "multiple_choice",
                "options": ["Vegetarian", "Non-vegetarian", "Vegan", "No preference"],
                "is_required": True,
                "order": 7,
                "placeholder": None
            },
            {
                "question_text": "Any special requirements or things you want to do?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 8,
                "placeholder": "eg. need wheelchair access, want to try local food"
            }
        ]
    },
    {
        "name": "Adventure Trip",
        "description": "For thrill seekers and outdoor enthusiasts",
        "icon": "🏔️",
        "is_custom": False,
        "questions": [
            {
                "question_text": "What is your fitness level?",
                "question_type": "single_choice",
                "options": ["Beginner", "Intermediate", "Advanced", "Expert"],
                "is_required": True,
                "order": 1,
                "placeholder": None
            },
            {
                "question_text": "What is your budget per day?",
                "question_type": "single_choice",
                "options": ["Under ₹500", "₹500-1000", "₹1000-2000", "₹2000-5000", "Above ₹5000"],
                "is_required": True,
                "order": 2,
                "placeholder": None
            },
            {
                "question_text": "Which adventure activities interest you?",
                "question_type": "multiple_choice",
                "options": ["Trekking", "River rafting", "Paragliding", "Camping", "Rock climbing", "Scuba diving", "Bungee jumping", "Skiing"],
                "is_required": True,
                "order": 3,
                "placeholder": None
            },
            {
                "question_text": "Accommodation preference?",
                "question_type": "single_choice",
                "options": ["Tent/Camping", "Hostel", "Budget hotel", "Mid range hotel", "No preference"],
                "is_required": True,
                "order": 4,
                "placeholder": None
            },
            {
                "question_text": "How many days?",
                "question_type": "single_choice",
                "options": ["2-3 days", "4-5 days", "6-7 days", "More than a week"],
                "is_required": True,
                "order": 5,
                "placeholder": None
            },
            {
                "question_text": "Any medical conditions we should know about?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 6,
                "placeholder": "eg. asthma, fear of heights, knee problems"
            },
            {
                "question_text": "Experience level with adventure sports?",
                "question_type": "single_choice",
                "options": ["First timer", "Done it once or twice", "Experienced", "Expert"],
                "is_required": True,
                "order": 7,
                "placeholder": None
            }
        ]
    },
    {
        "name": "Party Trip",
        "description": "For those who want to celebrate and have fun",
        "icon": "🎉",
        "is_custom": False,
        "questions": [
            {
                "question_text": "What is your budget per day?",
                "question_type": "single_choice",
                "options": ["Under ₹1000", "₹1000-2000", "₹2000-5000", "Above ₹5000"],
                "is_required": True,
                "order": 1,
                "placeholder": None
            },
            {
                "question_text": "What kind of nightlife do you prefer?",
                "question_type": "multiple_choice",
                "options": ["Clubs", "Bars", "Beach parties", "House parties", "Live music", "Rooftop lounges"],
                "is_required": True,
                "order": 2,
                "placeholder": None
            },
            {
                "question_text": "Music preference?",
                "question_type": "multiple_choice",
                "options": ["Bollywood", "EDM", "Hip hop", "Rock", "Sufi", "No preference"],
                "is_required": False,
                "order": 3,
                "placeholder": None
            },
            {
                "question_text": "Accommodation preference?",
                "question_type": "single_choice",
                "options": ["Party hostel", "Budget hotel", "Mid range hotel", "Luxury hotel", "Airbnb"],
                "is_required": True,
                "order": 4,
                "placeholder": None
            },
            {
                "question_text": "How many days?",
                "question_type": "single_choice",
                "options": ["2-3 days", "4-5 days", "Long weekend", "A week"],
                "is_required": True,
                "order": 5,
                "placeholder": None
            },
            {
                "question_text": "Any dietary or drink restrictions?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 6,
                "placeholder": "eg. vegetarian, no alcohol"
            }
        ]
    },
    {
        "name": "Cultural Trip",
        "description": "Explore history, art and local culture",
        "icon": "🏛️",
        "is_custom": False,
        "questions": [
            {
                "question_text": "What is your budget per day?",
                "question_type": "single_choice",
                "options": ["Under ₹500", "₹500-1000", "₹1000-2000", "₹2000-5000", "Above ₹5000"],
                "is_required": True,
                "order": 1,
                "placeholder": None
            },
            {
                "question_text": "What cultural aspects interest you most?",
                "question_type": "multiple_choice",
                "options": ["Historical monuments", "Museums", "Local cuisine", "Art galleries", "Religious sites", "Folk performances", "Architecture"],
                "is_required": True,
                "order": 2,
                "placeholder": None
            },
            {
                "question_text": "How much walking are you comfortable with?",
                "question_type": "single_choice",
                "options": ["Minimal", "Moderate", "A lot", "No limit"],
                "is_required": True,
                "order": 3,
                "placeholder": None
            },
            {
                "question_text": "How many days?",
                "question_type": "single_choice",
                "options": ["2-3 days", "4-5 days", "6-7 days", "More than a week"],
                "is_required": True,
                "order": 4,
                "placeholder": None
            },
            {
                "question_text": "Any specific monuments or places you want to visit?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 5,
                "placeholder": "eg. Taj Mahal, Hampi ruins, Ajanta caves"
            },
            {
                "question_text": "Food preference?",
                "question_type": "multiple_choice",
                "options": ["Vegetarian", "Non-vegetarian", "Want to try local cuisine", "No preference"],
                "is_required": True,
                "order": 6,
                "placeholder": None
            }
        ]
    },
    {
        "name": "Custom",
        "description": "Pick the questions you want, edit them, or add your own",
        "icon": "📝",
        "is_custom": True,
        "questions": [
            {
                "question_text": "What's your budget per person for the whole trip?",
                "question_type": "single_choice",
                "options": ["Under ₹5,000", "₹5,000-10,000", "₹10,000-20,000", "₹20,000-40,000", "Above ₹40,000"],
                "is_required": True,
                "order": 1,
                "placeholder": None
            },
            {
                "question_text": "How many days do you have for this trip?",
                "question_type": "single_choice",
                "options": ["1-2 days", "3-4 days", "5-7 days", "8-12 days", "More than 2 weeks"],
                "is_required": True,
                "order": 2,
                "placeholder": None
            },
            {
                "question_text": "What kind of trip are you in the mood for?",
                "question_type": "multiple_choice",
                "options": ["Relaxing", "Adventure", "Nature & outdoors", "Culture & history", "Food", "Nightlife", "Spiritual", "Beach"],
                "is_required": True,
                "order": 3,
                "placeholder": None
            },
            {
                "question_text": "Do you prefer one base or hopping between places?",
                "question_type": "single_choice",
                "options": ["Stay in one place", "A couple of stops", "Multi-city route", "No preference"],
                "is_required": True,
                "order": 4,
                "placeholder": None
            },
            {
                "question_text": "How far are you willing to travel?",
                "question_type": "single_choice",
                "options": ["Nearby (within ~300km)", "Anywhere in the country", "International is fine"],
                "is_required": False,
                "order": 5,
                "placeholder": None
            },
            {
                "question_text": "How would you rate your preferred pace?",
                "question_type": "scale",
                "options": ["1", "5"],
                "is_required": False,
                "order": 6,
                "placeholder": None
            },
            {
                "question_text": "Any places you've already been or want to avoid?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 7,
                "placeholder": "e.g. been to Goa twice, avoid very cold places"
            },
            {
                "question_text": "Anything specific you really want to do or see?",
                "question_type": "text",
                "options": None,
                "is_required": False,
                "order": 8,
                "placeholder": "e.g. trekking, a specific festival, scuba diving"
            }
        ]
    }
]

async def seed_templates(db: AsyncSession):
    """Seed predefined templates into database if not already present"""
    
    # check if templates already exist
    result = await db.execute(select(Template))
    existing = result.scalars().all()
    
    if existing:
        print("✅ Templates already seeded")
        return

    print("🌱 Seeding templates...")

    for template_data in TEMPLATES:
        template = Template(
            id=str(uuid.uuid4()),
            name=template_data["name"],
            description=template_data["description"],
            icon=template_data["icon"],
            is_custom=template_data["is_custom"]
        )
        db.add(template)
        await db.flush()  # get template id before adding questions

        for q in template_data["questions"]:
            question = TemplateQuestion(
                id=str(uuid.uuid4()),
                template_id=template.id,
                question_text=q["question_text"],
                question_type=q["question_type"],
                options=q["options"],
                is_required=q["is_required"],
                order=q["order"],
                placeholder=q["placeholder"]
            )
            db.add(question)

    await db.commit()
    print("✅ Templates seeded successfully!")