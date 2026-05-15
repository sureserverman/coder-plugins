---
name: game-mechanics-design
description: Use when designing, balancing, or reviewing core game mechanics, the core game loop, compulsion loops, progression, or FTUE (first-time-user experience). Triggers on greenfield mechanic-design requests like "design a core loop", "design a mechanic", "what's the core loop here", "balance this", "design the onboarding", "design progression", "how should this game feel session to session", "design a roguelike loop", "design a survival loop", "design FTUE". Also triggers on review requests like "is this loop shallow", "does this mechanic have depth", "audit the onboarding flow", "why does this game feel grindy", "compulsion loop review". Grounded in Schell, Sylvester, and Nystrom.
---

# game-mechanics-design

Opinionated rules for designing the *atomic verb* of a game and the loops it lives in. Distilled from Jesse Schell (*The Art of Game Design*), Tynan Sylvester (*Designing Games*), and Robert Nystrom (*Game Programming Patterns*).

## The three loops

Every game has at least three nested loops. Design them in this order — never start with the meta loop.

1. **Moment-to-moment (the verb).** What does the player *do* every second? "Shoot, reload, take cover." "Plant, water, harvest." "Dodge, parry, riposte." If this isn't fun in isolation with no progression on top, **nothing on top will save it.**
2. **Core loop (the session).** A 30-second to 5-minute cycle: do the verb → get feedback → choose what to do next. This is where Schell's "atomic moments of fun" stack into a session.
3. **Meta loop (the campaign).** Persistent progression across sessions: levels, gear, story, unlocks. This *amplifies* a good core loop. It cannot create one.

If a designer wants to start at the meta loop ("we'll have a battle pass and three currencies"), stop them. Ship the moment-to-moment first.

## Depth vs shallow complexity (Schell)

Schell distinguishes:
- **Depth** = simple rules, large strategic space. Go, Chess, Tetris, *Into the Breach*. Few rules, lifetime of mastery.
- **Shallow complexity** = many rules, small strategic space. Most live-service games. Many systems, few real decisions.

**Rule:** every new rule must answer "what new *meaningful* decision does this open up?" If the answer is "none, but it's another thing to do," cut it.

## Sylvester's elegance

From *Designing Games*: an elegant mechanic generates many different play experiences from a small number of rules. Examples:
- *Doom*'s "monsters infight when hit by other monsters" — one rule, hundreds of emergent tactics.
- *Minecraft*'s "blocks store and place" — one rule, an entire genre.
- *Spelunky*'s "everything in the level can hurt everything else" — one rule, every level tells a different story.

**Test:** if you cut this mechanic, do at least three other emergent behaviors *also* disappear? If only one does, it's a feature, not a mechanic.

## Compulsion loop vs reward loop

A **reward loop** gives the player something predictable for an action: kill enemy → XP → level up → new ability. It's healthy and satisfying.

A **compulsion loop** weaponizes variable-ratio reinforcement: kill enemy → *chance* of loot → tier *chance* of rarity → reroll *chance* of stat. It exploits operant conditioning to keep players engaged past the point of fun.

**Rule:** if the design relies on variable-ratio rewards to retain players, ask *who benefits.* A roguelike using procgen loot is variable-ratio for emergent play. A mobile slot mechanic using variable-ratio for daily-active-user metrics is engagement extraction. Don't conflate the two.

## FTUE / onboarding loop

The onboarding loop is a temporary, exaggerated version of the core loop:
1. **Frequent, magnified rewards** — every action produces audible/visual feedback. (Dopamine hook to anchor the verb.)
2. **Reduced failure cost** — early deaths are forgiving or framed as learning, never punitive.
3. **One mechanic at a time** — introduce the verb in isolation, then add modifiers one per ~5 minutes.
4. **Teach by doing, never by reading** — modal text walls are a failure mode. The level itself must teach.
5. **Dissolve smoothly** — by the time the player exits FTUE, rewards have throttled down to the steady-state core loop's cadence. Abrupt drops cause churn.

See [[game-ux-onboarding]] for the UX side (HUD, signposting, modal usage).

## Pacing — Sylvester's tension curve

A session should feel like a wave, not a flat line. Design intentional tension peaks and troughs:
- **Rest beats** between intense beats. Players need recovery to feel intensity. A two-hour Souls boss rush is exhausting and stops being meaningful.
- **Crescendo at the third** — long sessions: rising tension, climax around minute 20–30, deliberate cooldown, then a hook to return.
- **Save state at troughs, not peaks** — players who quit mid-peak return frustrated; players who quit at a trough return excited.

## Progression pacing rules

1. **Power curve > content curve.** New content must arrive faster than new player power, or the game trivializes itself.
2. **Make the player choose, don't automate the choice.** Skill trees that auto-allocate XP rob the player of the meta decision.
3. **One axis at a time.** Don't introduce stat upgrades, gear, talents, and runes in the first hour. Stage them across the first 5–10 hours.
4. **Caps as commitments, not punishments.** A soft cap that asks "where do you go next" is good. A hard cap that says "you can't do this any more" without a *why* is rage-quit material.
5. **Visible long-term goals.** Show the player what's possible at hour 30 from hour 1. Skill trees, mounts, raid bosses — *visible aspirations* drive retention.

## When you're designing a new mechanic — checklist

For each new mechanic, answer:

1. **Verb.** What does the player physically do? One sentence.
2. **Purpose.** What hole in the existing toolkit does this fill?
3. **Decision.** What choice does this open up that didn't exist before?
4. **Depth.** What emergent interactions exist with other mechanics?
5. **Feel.** What is the moment-to-moment sensation — power, dread, precision, chaos? (Hand off to [[game-feel-and-juice]].)
6. **Failure mode.** When the player misuses it, what happens? Punishing? Frustrating? Funny?
7. **Teaching.** How does the *level* teach this mechanic without text?
8. **Accessibility.** Can a one-handed player do this? A colorblind player? See [[game-accessibility-audit]].
9. **Cost.** Engine cost, content cost, balancing cost. Is the depth worth the build?

If steps 3 or 4 are weak, the mechanic is decoration, not a mechanic. Cut it.

## Anti-patterns

- **Feature creep masquerading as depth.** Three new systems are not depth; they're three new walls between the player and fun.
- **Punishing failure without teaching from it.** Permadeath only works when the death tells you *why*.
- **Grinding as content.** Time-walls are a content-cost-saving technique pretending to be a mechanic.
- **Tutorialization that won't let you play.** A 20-minute scripted intro before the player can move is a failure of teaching design. *Mario 1-1* taught a generation in 30 seconds with no text.
- **The "second game" trap.** A mini-game inside the game that isn't connected to the core loop is wasted depth.

## Procedure (when a designer asks for help)

1. **What's the verb?** Get a one-sentence answer to "what does the player do every second." If they can't answer, the design isn't ready — start there.
2. **What's the core loop?** 30 seconds to 5 minutes, what's the cycle? Diagram it.
3. **What's the depth?** Apply the elegance test — does this mechanic generate at least 3 emergent behaviors?
4. **What's the compulsion vs reward split?** Variable-ratio is fine if the player benefits; flag it if the *business* benefits.
5. **FTUE?** Are they teaching by doing, or by reading? Is the first 5 minutes the *core loop in miniature*, or a different game entirely?
6. **Pacing?** Where are the rest beats? Where's the crescendo?
7. **Output a brief** the engineer can implement: verb, loop, decisions opened, feel target, teaching plan, accessibility considerations.

Hand off implementation to [[game-architecture-patterns]] for code shape and [[game-feel-and-juice]] for tuning.

## Sources

- Schell, *The Art of Game Design: A Book of Lenses*, 3rd ed., CRC Press.
- Sylvester, *Designing Games: A Guide to Engineering Experiences*, O'Reilly, 2013.
- Nystrom, *Game Programming Patterns*, https://gameprogrammingpatterns.com/
- gamedesignskills.com — Core Gameplay Loop primer (cross-referenced).
- Skeleton Code Machine — "What is a core game loop?" (cross-referenced).

When this gets stale: re-read Schell's lens chapters on Elegance and Flow. The principles don't change; the genre framings do.
