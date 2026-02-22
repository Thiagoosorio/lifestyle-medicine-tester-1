"""Daily Growth data: meditation types, wisdom quotes, reflection prompts, mindfulness nudges."""

# ══════════════════════════════════════════════════════════════════════════════
# MEDITATION TYPES
# ══════════════════════════════════════════════════════════════════════════════

MEDITATION_TYPES = {
    "guided": {
        "label": "Guided",
        "description": "Following verbal instructions or a teacher's guidance",
    },
    "unguided": {
        "label": "Silent / Unguided",
        "description": "Self-directed silent sitting practice",
    },
    "breathing": {
        "label": "Breathwork",
        "description": "Focused breathing exercises (box breathing, 4-7-8, etc.)",
    },
    "body_scan": {
        "label": "Body Scan",
        "description": "Progressive body awareness from head to toe",
    },
    "walking": {
        "label": "Walking Meditation",
        "description": "Mindful, slow walking with full attention to movement",
    },
}

MOOD_LABELS = {
    1: "Agitated",
    2: "Restless",
    3: "Neutral",
    4: "Calm",
    5: "Very calm",
}

# ══════════════════════════════════════════════════════════════════════════════
# WISDOM QUOTES — 64 entries
# Sources: public-domain Stoic texts, publicly attributed statements
# ══════════════════════════════════════════════════════════════════════════════

WISDOM_QUOTES = [
    # ── Marcus Aurelius — Meditations (public domain, ~170 AD) ──────────────
    {"text": "You have power over your mind, not outside events. Realize this, and you will find strength.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "equanimity"},
    {"text": "The happiness of your life depends upon the quality of your thoughts.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "awareness"},
    {"text": "Waste no more time arguing about what a good man should be. Be one.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "self_discipline"},
    {"text": "Very little is needed to make a happy life; it is all within yourself, in your way of thinking.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "simplicity"},
    {"text": "When you arise in the morning, think of what a precious privilege it is to be alive, to breathe, to think, to enjoy, to love.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "presence"},
    {"text": "The soul becomes dyed with the colour of its thoughts.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "awareness"},
    {"text": "Accept the things to which fate binds you, and love the people with whom fate brings you together, and do so with all your heart.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "compassion"},
    {"text": "Never esteem anything as of advantage to you that will make you break your word or lose your self-respect.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "self_discipline"},
    {"text": "It is not death that a man should fear, but he should fear never beginning to live.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "presence"},
    {"text": "The best revenge is not to be like your enemy.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "equanimity"},
    {"text": "How much time he gains who does not look to see what his neighbour says or does or thinks, but only at what he does himself.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "self_discipline"},
    {"text": "Dwell on the beauty of life. Watch the stars, and see yourself running with them.", "author": "Marcus Aurelius", "source": "Meditations", "theme": "presence"},

    # ── Epictetus — Discourses / Enchiridion (public domain, ~135 AD) ──────
    {"text": "It is not what happens to you, but how you react to it that matters.", "author": "Epictetus", "source": "Discourses", "theme": "equanimity"},
    {"text": "We cannot choose our external circumstances, but we can always choose how we respond to them.", "author": "Epictetus", "source": "Discourses", "theme": "equanimity"},
    {"text": "First say to yourself what you would be; and then do what you have to do.", "author": "Epictetus", "source": "Discourses", "theme": "self_discipline"},
    {"text": "No man is free who is not master of himself.", "author": "Epictetus", "source": "Discourses", "theme": "self_discipline"},
    {"text": "Make the best use of what is in your power, and take the rest as it happens.", "author": "Epictetus", "source": "Enchiridion", "theme": "equanimity"},
    {"text": "He who laughs at himself never runs out of things to laugh at.", "author": "Epictetus", "source": "Discourses", "theme": "simplicity"},
    {"text": "If you want to improve, be content to be thought foolish and stupid.", "author": "Epictetus", "source": "Enchiridion", "theme": "self_discipline"},
    {"text": "Don't explain your philosophy. Embody it.", "author": "Epictetus", "source": "Discourses", "theme": "self_discipline"},
    {"text": "Wealth consists not in having great possessions, but in having few wants.", "author": "Epictetus", "source": "Discourses", "theme": "simplicity"},
    {"text": "The key is to keep company only with people who uplift you, whose presence calls forth your best.", "author": "Epictetus", "source": "Discourses", "theme": "compassion"},

    # ── Seneca — Letters to Lucilius / Moral Letters (public domain, ~65 AD)
    {"text": "We suffer more often in imagination than in reality.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "awareness"},
    {"text": "It is not that we have a short time to live, but that we waste a great deal of it.", "author": "Seneca", "source": "On the Shortness of Life", "theme": "presence"},
    {"text": "True happiness is to enjoy the present, without anxious dependence upon the future.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "presence"},
    {"text": "Luck is what happens when preparation meets opportunity.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "self_discipline"},
    {"text": "Begin at once to live, and count each separate day as a separate life.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "presence"},
    {"text": "Difficulties strengthen the mind, as labor does the body.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "equanimity"},
    {"text": "While we are postponing, life speeds by.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "presence"},
    {"text": "A gem cannot be polished without friction, nor a man perfected without trials.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "equanimity"},
    {"text": "Associate with people who are likely to improve you.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "compassion"},
    {"text": "Sometimes even to live is an act of courage.", "author": "Seneca", "source": "Letters to Lucilius", "theme": "equanimity"},

    # ── Thich Nhat Hanh — publicly attributed ──────────────────────────────
    {"text": "The present moment is filled with joy and happiness. If you are attentive, you will see it.", "author": "Thich Nhat Hanh", "source": "Peace Is Every Step", "theme": "presence"},
    {"text": "Feelings come and go like clouds in a windy sky. Conscious breathing is my anchor.", "author": "Thich Nhat Hanh", "source": "Stepping into Freedom", "theme": "awareness"},
    {"text": "Smile, breathe, and go slowly.", "author": "Thich Nhat Hanh", "source": "attributed", "theme": "simplicity"},
    {"text": "When you plant lettuce, if it does not grow well, you don't blame the lettuce.", "author": "Thich Nhat Hanh", "source": "attributed", "theme": "compassion"},
    {"text": "The miracle is not to walk on water. The miracle is to walk on the green earth, dwelling deeply in the present moment.", "author": "Thich Nhat Hanh", "source": "attributed", "theme": "presence"},
    {"text": "People have a hard time letting go of their suffering. Out of a fear of the unknown, they prefer suffering that is familiar.", "author": "Thich Nhat Hanh", "source": "attributed", "theme": "impermanence"},
    {"text": "To be beautiful means to be yourself. You don't need to be accepted by others. You need to accept yourself.", "author": "Thich Nhat Hanh", "source": "attributed", "theme": "compassion"},
    {"text": "Walk as if you are kissing the Earth with your feet.", "author": "Thich Nhat Hanh", "source": "Peace Is Every Step", "theme": "presence"},

    # ── Alan Watts — publicly attributed ───────────────────────────────────
    {"text": "The only way to make sense out of change is to plunge into it, move with it, and join the dance.", "author": "Alan Watts", "source": "The Wisdom of Insecurity", "theme": "impermanence"},
    {"text": "This is the real secret of life — to be completely engaged with what you are doing in the here and now.", "author": "Alan Watts", "source": "attributed", "theme": "presence"},
    {"text": "Muddy water is best cleared by leaving it alone.", "author": "Alan Watts", "source": "attributed", "theme": "equanimity"},
    {"text": "The meaning of life is just to be alive. It is so plain and so obvious and so simple.", "author": "Alan Watts", "source": "attributed", "theme": "simplicity"},
    {"text": "You are a function of what the whole universe is doing in the same way that a wave is a function of what the whole ocean is doing.", "author": "Alan Watts", "source": "attributed", "theme": "awareness"},
    {"text": "No valid plans for the future can be made by those who have no capacity for living now.", "author": "Alan Watts", "source": "attributed", "theme": "presence"},
    {"text": "To have faith is to trust yourself to the water. When you swim you don't grab hold of the water, because if you do you will sink.", "author": "Alan Watts", "source": "attributed", "theme": "equanimity"},
    {"text": "Every intelligent individual wants to know what makes him tick, and yet is at once fascinated and frustrated by the fact that oneself is the most difficult of all things to know.", "author": "Alan Watts", "source": "attributed", "theme": "awareness"},

    # ── Sam Harris — publicly attributed from interviews/books ─────────────
    {"text": "The quality of your mind is the quality of your life.", "author": "Sam Harris", "source": "Waking Up", "theme": "awareness"},
    {"text": "How we pay attention to the present moment largely determines the character of our experience and, therefore, the quality of our lives.", "author": "Sam Harris", "source": "Waking Up", "theme": "presence"},
    {"text": "The feeling that we call 'I' is an illusion. There is no discrete self or ego living like a Minotaur in the labyrinth of the brain.", "author": "Sam Harris", "source": "Waking Up", "theme": "awareness"},
    {"text": "There is nothing passive about mindfulness. One might even say that it expresses a specific kind of passion — a passion for discerning what is subjectively real in every moment.", "author": "Sam Harris", "source": "Waking Up", "theme": "awareness"},
    {"text": "Almost all our suffering is the product of our thoughts. We spend nearly every moment of our lives lost in thought.", "author": "Sam Harris", "source": "Waking Up", "theme": "awareness"},
    {"text": "The habit of spending nearly every waking moment lost in thought leaves us at the mercy of whatever our thoughts happen to be.", "author": "Sam Harris", "source": "Waking Up", "theme": "awareness"},
    {"text": "If you are perpetually angry, depressed, confused, and unloving, or your attention is elsewhere, it won't matter how successful you become.", "author": "Sam Harris", "source": "attributed", "theme": "presence"},
    {"text": "Everything we want to accomplish — to paint beautifully, to communicate clearly, to build a great business — requires that we pay close attention.", "author": "Sam Harris", "source": "attributed", "theme": "presence"},

    # ── Lao Tzu — Tao Te Ching (public domain, ~6th century BC) ────────────
    {"text": "Nature does not hurry, yet everything is accomplished.", "author": "Lao Tzu", "source": "Tao Te Ching", "theme": "simplicity"},
    {"text": "When I let go of what I am, I become what I might be.", "author": "Lao Tzu", "source": "Tao Te Ching", "theme": "impermanence"},
    {"text": "Knowing others is intelligence; knowing yourself is true wisdom. Mastering others is strength; mastering yourself is true power.", "author": "Lao Tzu", "source": "Tao Te Ching", "theme": "self_discipline"},
    {"text": "Be content with what you have; rejoice in the way things are. When you realize there is nothing lacking, the whole world belongs to you.", "author": "Lao Tzu", "source": "Tao Te Ching", "theme": "simplicity"},
]


# ══════════════════════════════════════════════════════════════════════════════
# REFLECTION PROMPTS — mapped to quote themes
# ══════════════════════════════════════════════════════════════════════════════

REFLECTION_PROMPTS = {
    "awareness": [
        "What did you notice today that you usually overlook?",
        "When was the last time you observed your own thoughts without reacting?",
        "What pattern in your thinking have you become aware of recently?",
    ],
    "impermanence": [
        "What are you holding onto that you could gently release?",
        "How has something you once feared losing already changed?",
        "What in your life today would you have wished for a year ago?",
    ],
    "presence": [
        "What moment today were you most fully present?",
        "When you find your mind wandering, where does it usually go?",
        "What would change if you gave your full attention to just this moment?",
    ],
    "equanimity": [
        "What recent difficulty can you view as a teacher rather than an obstacle?",
        "When did you last feel the urge to react — and chose not to?",
        "What would it look like to accept this situation exactly as it is?",
    ],
    "self_discipline": [
        "What small promise did you keep to yourself today?",
        "Where in your life is the gap between what you value and what you do?",
        "What would the best version of yourself do with the next hour?",
    ],
    "compassion": [
        "How did you show kindness — to yourself or someone else — today?",
        "Who in your life deserves more of your patience?",
        "What would you say to a friend going through what you're going through?",
    ],
    "simplicity": [
        "What could you remove from your day to make space for what matters?",
        "When did you last feel content with exactly what you have?",
        "What unnecessary complexity are you carrying?",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# MINDFULNESS NUDGES — 35 short daily micro-prompts
# ══════════════════════════════════════════════════════════════════════════════

MINDFULNESS_NUDGES = [
    "Before your next meal, take three breaths and notice the colors on your plate.",
    "Feel the weight of your body in the chair right now.",
    "For the next sixty seconds, listen to whatever sounds are present.",
    "Notice the temperature of the air on your skin.",
    "The next time you walk through a doorway, pause for one breath.",
    "Look at something nearby as if you are seeing it for the first time.",
    "Feel the ground beneath your feet. You are here.",
    "Take one breath where the exhale is twice as long as the inhale.",
    "Notice three things in your field of vision that you hadn't noticed before.",
    "Place your hand on your chest and feel your heartbeat for ten seconds.",
    "Before you speak next, take one conscious breath.",
    "Notice the sensation in your hands right now. Warm? Cool? Tingling?",
    "Close your eyes for five seconds and simply listen.",
    "The next glass of water you drink, notice the sensation of each sip.",
    "Right now, soften your jaw, drop your shoulders, and unclench your hands.",
    "Look at the sky. Just look.",
    "Notice the space between two sounds.",
    "When you wash your hands today, feel the water as if for the first time.",
    "Before you check your phone, take one breath first.",
    "Notice where in your body you are holding tension right now.",
    "Feel the texture of whatever your hands are touching.",
    "The next person you see, silently wish them well.",
    "Notice the pause at the top of your inhale, before the exhale begins.",
    "Step outside for thirty seconds and notice what the air smells like.",
    "Before your next task, ask yourself: what is actually needed right now?",
    "Count five breaths. Just five. Then return to whatever you were doing.",
    "Notice the colors around you. Really see them.",
    "When you eat your next bite of food, chew it twice as slowly as usual.",
    "Find something in the room that is still. Rest your attention on it.",
    "Notice the rising and falling of your abdomen with each breath.",
    "The next time you wait — in line, at a light — instead of reaching for your phone, just stand.",
    "Listen to the most distant sound you can hear.",
    "Place both feet flat on the floor and feel the contact.",
    "For one minute, do nothing. Absolutely nothing.",
    "Notice what emotion is present right now, without trying to change it.",
]
