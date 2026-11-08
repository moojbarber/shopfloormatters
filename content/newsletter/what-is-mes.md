---
subject: "You already have an MES."
preview: "It's just made of paper travellers, whiteboards, spreadsheets and what people remember."
---
Hi {{ subscriber.first_name | default: "there" }},

Welcome to Shopfloor Matters, and thank you for signing up.

Each email in this series takes one article from the site and gives you the useful part straight away, in about five minutes. If you want to go deeper, the full article is one click away. They'll come weekly for the first couple of months, then every fortnight, following the learning paths on the site: we start with the foundations and work up to shopfloor AI and the business case for it.

If you ever have a question about your own project, just hit reply. It comes straight to me.

So, let's start at the beginning.

## Most factories already have an MES

It just isn't software.

It's paper travellers and whiteboards, Excel spreadsheets, a database someone in quality built years ago, and ERP screens pushed onto the shopfloor where they were never designed to be. Each piece manages part of the operation. None of them talk to each other, and the knowledge that holds it all together lives in people's heads.

That's what MES/MOM replaces.

## Two terms, two scopes

**MES**, the manufacturing execution system, is production execution: getting the right order onto the right line, then recording what actually happened. Counts, scrap, downtime and OEE, ideally straight from the equipment, with actuals going back to ERP instead of estimates.

**MOM**, manufacturing operations management, is the whole operation. ISA-95 splits manufacturing operations into four areas, and MOM covers all of them: production, quality, inventory and maintenance.

The difference sounds academic until you think about downtime. Production cares about it, and so does maintenance. If they record it in separate systems, the morning meeting starts with a debate about whose numbers are right.

Now think about the operator. Within the same ten minutes they run the order, do the quality check, consume the material and carry out the autonomous maintenance. On one platform, that's one application and one login, and everything they record is visible to everyone who needs it.

## A quick test for your own factory

Take one stoppage from last week and follow it through. Ask:

1. Where was it first recorded, and by whom?
2. How many systems or spreadsheets does it appear in now?
3. Do production and maintenance agree on how long it lasted?
4. Can you tell which order, and which batch of material, was running at the time?

If the answers involve more than one system, or a shrug, you've found the gap MES/MOM is built to close.

## Why it matters even more now

AI learns from accurate, contextualised data collected over time. A machine signal that says "stopped" means little on its own. MES/MOM turns it into "Line 7 stopped at 14:23 during order 4521, on night shift, for 12 minutes, because of a jam at station 2, for the third time in 48 hours."

That's data a model can learn from. The broader the scope, the richer the context.

## My view

I've used the two terms interchangeably for years, but the distinction is worth being deliberate about when you buy. The most expensive mistake I see is drifting into four or five point solutions, each one bought because it solved a single problem quickly. A cheap stop-gap is rarely cheap by the time it's integrated.

[[button: Read the full guide to MES/MOM]]

The full article covers what each of the four pillars does in practice, and where MES/MOM sits alongside ERP.

**Next time:** where MES came from, from the first PLC in 1969 to the cloud, and what that history says about where AI fits.

Speak soon,

Matt

P.S. If you'd like to see which systems your factory runs on today, and where the gaps are, the [systems landscape builder](/tools/systems-landscape) maps it in a few minutes.
