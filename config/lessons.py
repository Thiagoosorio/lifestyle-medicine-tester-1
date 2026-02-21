"""Daily Micro-Lesson content: CBT-based 5-minute lessons mapped to ACLM pillars."""

# Each lesson: (pillar_id, title, content, quiz_question, quiz_options_csv, quiz_answer_index, lesson_type, difficulty)
LESSON_LIBRARY = [
    # ── Nutrition (pillar 1) ─────────────────────────────────────────────────
    (1, "The Power of Whole Foods",
     """**What are whole foods?** Foods that are minimally processed and close to their natural state — fruits, vegetables, whole grains, legumes, nuts, and seeds.

**Why it matters:** The American College of Lifestyle Medicine recommends a whole-food, plant-predominant diet because it:
- Reduces inflammation
- Lowers risk of heart disease, diabetes, and some cancers
- Supports healthy gut microbiome

**Your 2-minute action:** Look at your next meal. Can you swap one processed item for a whole food? (e.g., white bread → whole grain, chips → almonds)""",
     "Which of these is a whole food?",
     "White bread,Brown rice,Fruit juice,Protein bar", 1, "article", 1),

    (1, "The Fiber Effect",
     """**Why fiber is your secret weapon:** Most people get only 15g of fiber daily — the target is 25-35g.

**What fiber does:**
- Feeds beneficial gut bacteria
- Keeps you full longer (reduces overeating)
- Stabilizes blood sugar
- Lowers cholesterol

**Top fiber sources:** Lentils (15g/cup), black beans (15g/cup), avocado (10g), broccoli (5g/cup), oats (4g/cup)

**Your 2-minute action:** Add one high-fiber food to your shopping list.""",
     "What is the daily recommended fiber intake?",
     "10-15g,15-20g,25-35g,50g+", 2, "article", 1),

    (1, "Mindful Eating 101",
     """**What is mindful eating?** Paying full attention to the experience of eating — the taste, texture, and sensation of each bite.

**Why it works:** Studies show mindful eating reduces binge eating, improves satisfaction, and helps with portion control.

**The 5-4-3-2-1 Eating Exercise:**
- **5** deep breaths before eating
- **4** seconds to chew each bite
- **3** senses engaged (sight, smell, taste)
- **2** minute pause halfway through your meal
- **1** moment of gratitude for the food

**Your 2-minute action:** At your next meal, put your fork down between bites.""",
     "What does mindful eating primarily help with?",
     "Counting calories,Paying attention to the eating experience,Eating faster,Avoiding all snacks", 1, "exercise", 2),

    # ── Physical Activity (pillar 2) ─────────────────────────────────────────
    (2, "The Minimum Effective Dose",
     """**How much exercise do you really need?** The WHO recommends:
- **150 minutes/week** of moderate activity (brisk walking, cycling), OR
- **75 minutes/week** of vigorous activity (running, HIIT)
- Plus **2 days** of strength training

**The key insight:** Even 10 minutes of walking after a meal significantly improves blood sugar levels. You don't need an hour — consistency beats intensity.

**Your 2-minute action:** Set a timer for 10 minutes. Walk. That's it.""",
     "What is the WHO recommendation for moderate physical activity per week?",
     "30 minutes,75 minutes,150 minutes,300 minutes", 2, "article", 1),

    (2, "Movement Snacking",
     """**What are movement snacks?** Brief 2-5 minute bursts of activity throughout the day instead of one long workout.

**Examples:**
- 5 squats every time you go to the bathroom
- Walk while on phone calls
- 2-minute stretch break every hour
- Take the stairs always
- Park further away

**The science:** Research from the University of Utah shows that even 2-minute walks every hour reduce mortality risk by 33%.

**Your 2-minute action:** Stand up right now. Do 5 squats. Sit back down. You just movement-snacked!""",
     "How short can an effective movement snack be?",
     "30 minutes,15 minutes,2-5 minutes,1 hour", 2, "exercise", 1),

    (2, "The Talk Test for Exercise Intensity",
     """**How hard should you exercise?** Use the Talk Test:
- **Light:** Can sing while exercising
- **Moderate:** Can talk but not sing (THIS is the sweet spot)
- **Vigorous:** Can only say a few words

**Why moderate is magic:** Moderate-intensity exercise burns fat efficiently, strengthens the heart, and is sustainable long-term. It feels like "comfortably uncomfortable."

**Your 2-minute action:** During your next walk, check: can you talk but not sing? That's your moderate zone.""",
     "During moderate exercise, you should be able to:",
     "Sing a song,Talk but not sing,Only say a few words,Not talk at all", 1, "article", 2),

    # ── Sleep (pillar 3) ─────────────────────────────────────────────────────
    (3, "Sleep Hygiene Basics",
     """**Your bedroom is for 2 things:** Sleep and intimacy. That's it.

**The Big 5 Sleep Rules:**
1. **Consistent schedule** — Same bedtime and wake time every day (yes, weekends too)
2. **Cool and dark** — 65-68°F (18-20°C), blackout curtains
3. **No screens 30 min before bed** — Blue light suppresses melatonin
4. **No caffeine after 2 PM** — Caffeine's half-life is 5-6 hours
5. **Wind-down ritual** — Read, stretch, meditate, or journal

**Your 2-minute action:** Set a phone alarm for 30 minutes before your target bedtime labeled "Screens Off."

""",
     "What temperature is ideal for sleep?",
     "72-75°F (22-24°C),65-68°F (18-20°C),60-62°F (15-17°C),78-80°F (25-27°C)", 1, "article", 1),

    (3, "The Cortisol-Sleep Connection",
     """**Why you can't sleep when stressed:** Cortisol (stress hormone) and melatonin (sleep hormone) are inversely related. When cortisol is high, melatonin can't do its job.

**The solution: the physiological sigh.** This is the fastest evidence-based way to lower cortisol:
1. Double inhale through the nose (two quick breaths in)
2. Long, slow exhale through the mouth
3. Repeat 3 times

**Why it works:** The double inhale maximally inflates the alveoli in your lungs, and the long exhale activates the parasympathetic nervous system (rest and digest).

**Your 2-minute action:** Try 3 physiological sighs right now. Notice how your body feels after.""",
     "The physiological sigh involves:",
     "One deep breath in and out,Double inhale then long exhale,Holding breath for 30 seconds,Breathing in through the mouth", 1, "exercise", 2),

    # ── Stress Management (pillar 4) ─────────────────────────────────────────
    (4, "Box Breathing for Instant Calm",
     """**Box breathing** is used by Navy SEALs to stay calm under pressure. It works anywhere, anytime.

**How to do it:**
- **Inhale** through your nose for 4 counts
- **Hold** for 4 counts
- **Exhale** through your mouth for 4 counts
- **Hold** for 4 counts
- Repeat 4 rounds

**The science:** This activates your vagus nerve, shifting your nervous system from fight-or-flight to rest-and-digest in under 2 minutes.

**Your 2-minute action:** Do 4 rounds of box breathing right now. Set a timer if needed.""",
     "How many counts do you hold your breath in box breathing?",
     "2 counts,4 counts,6 counts,8 counts", 1, "exercise", 1),

    (4, "Cognitive Reframing 101",
     """**What is cognitive reframing?** Changing the way you think about a situation to change how you feel about it.

**The ABC Model (from CBT):**
- **A** = Activating Event (what happened)
- **B** = Belief (what you think about it)
- **C** = Consequence (how you feel/act)

**The key insight:** It's not A that causes C — it's B! You can't always control events, but you can change your beliefs about them.

**Example:**
- Event: "I missed my workout"
- Unhelpful belief: "I'm lazy and I'll never change"
- Reframe: "I missed one day. My streak is still strong. I'll go tomorrow."

**Your 2-minute action:** Think of a recent frustration. What was your belief? Can you reframe it?""",
     "In the ABC model, what causes your emotional response?",
     "The event itself,Your belief about the event,Other people,The weather", 1, "reflection", 2),

    (4, "The 5-4-3-2-1 Grounding Technique",
     """**When anxiety hits, ground yourself with your senses:**

Look around and identify:
- **5** things you can SEE
- **4** things you can TOUCH
- **3** things you can HEAR
- **2** things you can SMELL
- **1** thing you can TASTE

**Why it works:** This technique interrupts the anxiety spiral by forcing your brain to focus on the present moment through sensory input. It activates the prefrontal cortex and calms the amygdala.

**Your 2-minute action:** Try it now, wherever you are. Name each item out loud or in your mind.""",
     "How many things do you identify that you can SEE in the 5-4-3-2-1 technique?",
     "1,3,5,10", 2, "exercise", 1),

    # ── Social Connection (pillar 5) ─────────────────────────────────────────
    (5, "The Science of Loneliness",
     """**Loneliness is as dangerous as smoking 15 cigarettes a day.** This isn't hyperbole — it's from a meta-analysis of 148 studies.

**What loneliness does to your body:**
- Increases inflammation (raises CRP levels)
- Weakens immune function
- Raises cortisol chronically
- Increases risk of heart disease by 29%

**The cure isn't more people — it's deeper connection.** One meaningful conversation per day is more powerful than 100 surface interactions.

**Your 2-minute action:** Text someone you care about right now. Not "hey," but something specific: "I was thinking about [shared memory] and it made me smile."
""",
     "Loneliness is comparable in health risk to:",
     "Eating fast food daily,Smoking 15 cigarettes a day,Skipping breakfast,Not stretching", 1, "article", 1),

    (5, "Active Listening",
     """**Most people listen to reply, not to understand.** Active listening changes everything.

**The HEAR technique:**
- **H**alt — Stop what you're doing. Put the phone away.
- **E**ngage — Make eye contact. Lean in slightly.
- **A**nticipate — Be curious about what they'll say next (not what you'll say).
- **R**eplay — Reflect back what you heard: "So what you're saying is..."

**Why it matters:** When people feel truly heard, trust deepens dramatically. Active listening is the #1 skill for improving all relationships.

**Your 2-minute action:** In your next conversation, try the HEAR technique. Notice the difference.""",
     "What does the 'R' in HEAR stand for?",
     "Respond,React,Replay,Reject", 2, "exercise", 2),

    # ── Substance Avoidance (pillar 6) ────────────────────────────────────────
    (6, "Understanding Cravings",
     """**A craving is not a command.** It's a wave — it rises, peaks, and passes. The average craving lasts only 15-20 minutes.

**The RAIN technique for cravings:**
- **R**ecognize — "I'm having a craving"
- **A**llow — Don't fight it. Let it be there.
- **I**nvestigate — Where do you feel it? What triggered it?
- **N**on-identify — "I am not my craving. I am a person having a craving."

**Urge surfing:** Imagine the craving as a wave. You're a surfer riding it. It will rise, peak, and crash. You just have to stay on the board for 15-20 minutes.

**Your 2-minute action:** Next time a craving hits, set a 20-minute timer. Observe it without acting on it.""",
     "How long does the average craving last?",
     "5 minutes,15-20 minutes,1 hour,All day", 1, "article", 1),

    (6, "Alcohol: What the Science Really Says",
     """**No amount of alcohol is "safe."** The 2023 WHO statement is clear: the risk of harm starts from the first drop.

**What alcohol does:**
- Disrupts sleep architecture (even 1 drink reduces REM sleep)
- Increases anxiety the next day ("hangxiety")
- Impairs muscle recovery by 30-40%
- Is a Group 1 carcinogen (same category as tobacco)

**If you choose to drink:** The less, the better. But if you're reducing:
- Replace the ritual, not just the drink (sparkling water + lime, herbal tea, mocktails)
- Identify your triggers (social pressure, stress, boredom, habit)
- Track alcohol-free days — celebrate them

**Your 2-minute action:** If you drink, count your alcohol-free days this week. Celebrate each one.""",
     "What category of carcinogen is alcohol classified as by WHO?",
     "Not a carcinogen,Group 3 (possible),Group 2 (probable),Group 1 (confirmed)", 3, "article", 2),
]
