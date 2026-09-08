# Competitive analysis — the working method

The procedure behind `/business:market-research` and the `market-researcher` agent.
It condenses, in this plugin's own words, the method in Denis Dovgopoliy's
*Competitive analysis for startups: methodology* (v3.2.6, 2026-08-23) — an
eighteen-section working procedure for a company entering a global market. The
handbook itself is not reproduced here; this file states what the tool does with it.
Steps 1–10 are mandatory at `standard`+; 11–15 are the `deep` extras; 16–18 are the
limits every tier respects. The numbered headings in this file match the handbook's so a reader
holding it can cross-check.

## 1 — Who counts as a competitor

**A competitor is anyone who solves the same problem** — not anyone with a similar
product, in the same market, or in the same industry category. That pulls non-product
answers into the list: a manual procedure, a service, the customer's own internal build,
a spreadsheet, a general-purpose tool configured for the job.

"We have no competitors" is never a finding. It means the list was built badly, or there
is no money in the market. Either way it is reported as a **failed coverage check**, not
as an absence of competition.

Three classes, each recorded on every row:

- **direct** — solving this problem *is* their business. They do not retreat; expect
  attrition. (Exception: they move into an adjacent niche — temporary, they can return.)
- **indirect** — the competing product is a side line. These are **partner candidates**
  (§ 12 — Indirect competitors are partner candidates), not enemies.
- **non-consumption** — the customer finds nothing acceptable and does nothing. It never
  enters the table; it **must** enter the market estimate. Measured by the share of deals
  lost to "no decision".

## 2 — Building the list — three passes

Each pass yields companies the other two miss. Run all three; say which pass found each
row.

1. **Category pass.** Search by product category, ads bought against category queries,
   industry databases, market maps. Finds direct competitors; exhausts fast.
2. **Customer-job pass.** State the job as *"when [situation], I want to [action], so
   that [outcome]"*, then list every way that outcome is reached today. Classify each:
   same job same method / same job **different method** / different job with a
   conflicting outcome. The second class produces the most dangerous competitors and
   almost never surfaces in the category pass.
3. **Alternatives pass.** What would the customer do if this product did not exist? A
   spreadsheet, a hired person, an existing general-purpose tool, nothing.

A wrong job statement invalidates everything built on it, positioning included — which is
why the skill confirms the statement with the operator **before** dispatching.

## 3 — Coverage — when to stop

- Fewer than **20** competitors on a global market means the search is not finished.
- The stop criterion is a **rate**, not a count: when the time per newly found competitor
  grows several-fold, the search is exhausted. Report `coverage: exhausted` only then;
  otherwise `coverage: open`, with the count and the passes run.
- Homogeneous companies **collapse into one row** as a group. On a crowded market: several
  dozen found, reduced to 4–6 groups with subgroups, plus the ones that refuse to group
  standing alone. `competitors:` in the artifact frontmatter counts **rows** (groups +
  standalones), and the body states the raw count.

## 4 — Sources — where the evidence is

Cite the source class alongside the URL. Each reads for something specific:

| Source | What it tells you |
|---|---|
| Professional networks / social | founders' and management's background, news, audience response, headcount trend |
| Company & funding databases | what has already been funded against this idea |
| Industry databases (paid) | a structured view of the segment — a source of facts, not of the picture (§ 18 — Limits — respected at every tier) |
| **Job boards** | skills/tech overlap with your stack = work on an adjacent product; posting geography = where the team actually sits; an isolated cluster of postings = an undeclared effort |
| **Q&A / discussion sites** | the primary source on **unpublished pricing** and on what customers actually complain about |
| **Conference talks + slides** | the most productive source: a speaker reveals more than official communication allows; find the video — floor questions go deeper than the deck |
| Traffic data | the basis for sales-by-conversion estimates (§ 15 — Sizing a market with no data) |
| Website technology profiling | stack, integrations, platforms |
| Review platforms | perception, recurring complaints, the events that push a customer to look elsewhere |
| Employee reviews | how leadership is perceived; internal state |
| Patent databases | mandatory for deep tech / hardware / defense: filing dates, classes, citation networks, assignees, legal status → filing density by subdomain and the areas nobody files in |
| Press releases | boilerplate = how they want to be seen; body sometimes carries customer or revenue numbers |

## 5 — What to collect — six blocks

**Team.** The largest share of value: people make the decisions. Method is absorption
(articles, interviews, talks, prior companies, public positions), sufficiency test: *can
you answer "what will this person do if we do X?"* **Legal boundary: collect only public
professional history; never accumulate personal data.** Data-protection law applies in
every jurisdiction; what may be stored is agreed with counsel before the work starts. The
working rule is to not store it at all.

**Strategy.** Four levels: operations (visible), one-year horizon (hidden), two-to-three
year horizon (hidden), declared mission (public). Reconstruct the hidden two from traces —
release sequence, messaging shifts, audience movement, hiring, partnerships, patents. The
output is a **judgment about which branch they will take**, not a list of scenarios.

**Product.** Positioning first (it determines features and marketing, not the reverse),
then: full feature list with value and uniqueness, supported environments; minimum price,
average deal size, what drives price; strengths/weaknesses **as the customer perceives
them**; switching cost (depth of embedding); barriers (data network effects, network
effects, ecosystem); **sales model** from the price-to-complexity ratio — self-service /
transactional / enterprise — because their model decides what you can fight them with.
**A weakness is measured, not described**: customer need + direction + metric + target
value. Slow / manual / unreliable / inaccurate coverage of a need is a measured weakness
and the bar for your own solution.

**Marketing.** Every message from every material (site, boilerplate, press, blog,
whitepapers, video, ads): the story told, the value words, the one-sentence
self-description, audience response. Channels: where they advertise, which queries they
buy, which platforms, verticals, events.

**Metrics.** Numbers comparable across every competitor: headcount and trend, customer
count, revenue estimate, growth rate, traffic and sources, conversion, market share,
satisfaction. Estimation rules where data is missing: revenue from headcount × an industry
revenue-per-employee ratio adjusted for stage and sales model; customer count only to an
order of magnitude; market share at startup scale by a 200–300-respondent survey of the
segment. Every estimate states its method and inputs.

**Investment and organization.** Access to capital is an advantage in itself (prior
exits, investor roster, geography, network). A **large fresh round reads two ways**:
resources, and a frozen strategy — the product line is locked by the deal terms, so the
company is often less dangerous after the round than six months before it. Read the
investor roster across the category: a fund places one bet per category, so a prominent
fund absent from yours is a candidate to approach. M&A shows direction: buying from an
adjacent segment means entering it. Organization: the parts that cannot be copied —
leadership visibility, culture, processes, retention.

Collect **more than you think you need**: on a crowded market the working volume runs
past 60 parameters per company. The attributes that group competitors meaningfully often
sit outside the product (online-presence technicals, search behaviour, hiring structure,
communication language) and are found by sweeping collected data, never derived up front.
A parameter that yields nothing costs one column; one never collected is unavailable.

## 6 — Storage

Every finding carries a one-paragraph *why it was kept, what it concludes*. Without that,
searching your own archive takes longer than searching the open web within six months.
In this plugin: the artifact body is that archive, one cited line per claim, and the
`## Gaps` section is the list of what was searched and not found.

## 7 — The table

The main working artifact — `business/competitor-table.yaml`, spec in
`competitor-table-format.md`, tooling in `scripts/competitor-table.py`.

- **Rows:** competitors; companies with an identical attribute set collapse into one
  group row.
- **Columns:** characteristics in four categories — quantitative product, qualitative
  product, target market, company.
- **Geography** is scored by *difficulty of doing business*, not by country name, and by
  where engineering / marketing / business development actually sit, not the legal
  address. Verify against job postings, employee profiles, office addresses.
- **Four data types coexist:** number, percentage, binary flag, score. **Conversion rule:**
  anything that can be turned into a quantity is; a categorical value with no natural
  ordering expands into one binary column per value.

## 8 — Quadrants

The table is unreadable; the chart makes it readable.

- Two axes on a **–5 … +5** scale; zero is the centre (median or mean, by distribution);
  linear or logarithmic by the ratio between extremes; the third parameter is bubble
  radius (usually revenue or headcount). Distance is measured **between centres**; the
  gap between bubble edges means nothing.
- **No value judgments on the poles.** Many characteristics have their optimum inside the
  range. You want contrast, not evaluation; if "more = better" fails for the segment,
  invert the axis.
- **Find the axes by sweep.** Plot a triple, look, next triple. Intuition suggests the
  candidates; the sweep produces the configuration. You are looking for two things: **the
  point where you differ from everyone**, and **the zone where nobody is**. The sweep is
  also the grouping check: a group that stays together across several axis pairs is
  sound; one that scatters dissolves and the table is rebuilt.
- **An unattractive quadrant is not automatically unusable.** Low price + low complexity
  wins mass markets; high price + limited functionality works when it lifts the product
  into a higher segment by perception. Test: take the characteristic that makes the
  quadrant look losing and check whether a segment exists for which it is positive or
  neutral; if so, invert the axis. The upper-right is usually the most crowded — an
  argument against it.

## 9 — Trajectories

*`deep` tier.* The quadrant shows state; movement shows strategy. Add each company's state for the three
prior years, plot Y-2 → Y-1 → Y0 on the same axes, and connect them: a direction vector
plus a change in size. Companies are inertial, so extrapolate to Y+1 and Y+2. With
trajectories for everyone you hold a **map of directions**, and the target is **the zone
that will be empty in two years** — often one that looks dangerously crowded today.

**Size correction:** inertia is proportional to size. A small company turns 180° in a
quarter, so its vector predicts little; a large one can sit still for years, so its vector
is reliable and *not moving is itself information*. Record direction **and length** for
every company; length says how fast they move and how far the extrapolation can be
trusted.

**For an investor:** two charts — current positioning with a visible point of
differentiation, and trajectories with the reasoning for why the chosen zone will clear.

## 10 — Is the advantage durable?

The quadrant shows you are different; it does not show the difference will hold. **If a
competitor can copy you and it is rational for them to do so, the advantage is temporary,
whatever your growth rate.** A durable advantage = a **benefit** (lower cost or higher
price) + a **barrier** that makes copying impossible or unattractive. Seven barrier types:
scale economies, network effects, counter-positioning, switching costs, brand, cornered
resource, process power. A startup realistically starts with **one**: counter-positioning
— a business model the incumbent cannot copy without damaging its own. The rest are built
later, with the time counter-positioning bought.

- Barrier test: reproducible by hiring a consultant or poaching a team → not a barrier.
- Accumulated data volume is usually not a barrier: the curve flattens fast, and enough
  data competes with the most data.
- **Will the incumbent react?** An incumbent normally ignores an opportunity that adds
  less than ~10% to its enterprise value. Size your segment in *their* money and you have
  the estimate.

## 11 — Deriving positioning — five components, fixed order

1. **Competitive alternatives** — what the customer would do without you.
2. **Unique attributes** — what you have that the alternatives lack.
3. **Value with evidence** — what those attributes give the customer.
4. **The customers for whom that value is critical.**
5. **Market category** — last, because it is the frame around value already found.

The order is mandatory: value depends on unique capability; capability is unique only
relative to an alternative; the segment is defined by the value. Two ways to handle
category: enter an existing one against its leader, or **name and take a subcategory** —
the realistic option for a startup. The quadrant finds the empty zone; the five
components turn it into a statement.

## 12 — Indirect competitors are partner candidates

*`deep` tier.* Three questions and an offer. *What share of your revenue comes from the product that
competes with ours?* (usually low single digits — the product exists to cover a customer
need, not to earn). *What share of your development spend goes to it?* (almost always
higher than its revenue share: a side product needs dedicated people the main flow does
not supply). **The offer:** we supply a white-label version; your revenue stays, your
development / support / promotion cost disappears. Hard at MVP stage; closes readily with a
mature product and a defined customer base.

Limits: a single-partner company eventually faces *sell to us or lose the revenue*. Three
rules — hold your own direct revenue; keep any one partner below 20% of revenue (hard
ceiling 30%); hold no fewer than three partners. Then losing one is survivable and an
acquisition attempt becomes a negotiation among three. Such deals carry a right of first
refusal or a notify-on-sale clause; with several partners it works for you. Keep contact,
track their leadership's public statements, and catch the moment the side product becomes
a burden to them.

## 13 — Battlecard

*`deep` tier.* One page per priority competitor, for people who have not read the analysis: how they
position themselves, strong points, weak points, the standard customer objections in our
favour and in theirs, the conditions under which we win, and under which we lose. Updated
from the signals in § 14 — Continuous monitoring.

## 14 — Continuous monitoring

*`deep` tier.* A one-off analysis decays; a trajectory is a forecast that has to be confirmed or refuted.

1. Take the table.
2. Rank competitors by impact on current and future numbers — higher impact, higher
   monitoring priority.
3. For each priority competitor, define the situations that affect you: price change,
   product launch, channel change, entry into your geography, hiring against your stack,
   patent filing, funding round.
4. Convert each situation into an **indicator** — an observable event that precedes it.
5. Assign each indicator to whoever will notice it first by the nature of their work.
6. Consolidate in one place with a date and a source.

An indicator works in tandem with a trajectory: the trajectory says where the competitor
should go; the indicator confirms the move or shows the forecast was wrong.

**Testing hypotheses:** when several explanations are on the table, test them for
*incompatibility with known facts* rather than confirming the favourite — hypotheses as
columns, facts as rows, mark each incompatibility; the one with the fewest contradictions
survives. **Playing out moves:** the team plays what a specific competitor will do if you
do X; this only works with the people profiles (§ 5 — What to collect — six blocks), because the answer is given for
the individual who decides, not for the company.

## 15 — Sizing a market with no data

When no analyst covers the segment:

1. Find an **adjacent market** with published analytics, comparable in purchase model,
   price, and channel.
2. Extract its conversion — sales per unit of traffic.
3. List the players in the target segment and estimate their traffic.
4. Apply the adjacent conversion to the target traffic → a volume estimate.
5. Talk to several operators in the segment; some will name numbers — a calibration point.

Accuracy is in the tens of percent; for an enter/don't-enter decision that is enough.
The same principle sizes a single parameter: an unpublished price costs the customer
effort to learn, so someone has already asked in public — find where.

## 16–17 — Who does the work, and what an investor checks

Around 200 hours in the first year, and **not delegated**: anyone can collect data, but
only the person holding the strategy can say why a number matters. The main output is not
the document but the acquired ability to judge competitors' moves in day-to-day decisions.
In this plugin the agent collects and the operator judges — which is why the skill
confirms scope first and the artifact never carries a verdict.

An investor checks four things: that you spend time on this and treat it as important;
that you draw correct conclusions; that you can build strategy from it; that it runs
continuously rather than having been assembled before the meeting. A single number that
captures the market lands better than a large table; what lands hardest is a non-obvious
cut of the market that looks obvious in hindsight — a quadrant whose axes show your view
of the market and your strategy at once. An investor who knows your competitors better
than you do ends the conversation.

## 18 — Limits — respected at every tier

- **Not for product decisions.** Customers answer what to build next; a competitor may be
  acting at random, and copying imports their mistake.
- **Does not displace customer work.** The analysis shows the field; customers show the
  task.
- **Industry analytics are a lagging indicator.** Analyst quadrants record consensus after
  the shift, carry vendor input, define segments narrowly, reward size, and publish
  annually. Use them as a source of facts, never as the picture.
- **A trajectory is a hypothesis**, not knowledge; only monitoring confirms or refutes it.
- **A market leader gets less** from the method: nothing to orient against, so its value
  reduces to early detection of challengers.
