---
title: "Code, build, stitch or configure: four ways to run your shopfloor systems"
short: "Code, build, stitch or configure"
description: "Four ways to run shopfloor systems: code from scratch, build from blocks, stitch point solutions together, or configure a platform. The trade-offs of each."
published: 2026-08-26
category: advice
art: gates
---

Every so often a manufacturer with a strong internal IT team asks me whether they should just write their own MES. Some want to build applications on a low-code toolkit instead. Others ask whether they should buy the best tool for each job and connect them together. Others have already decided on a single platform and want to know how to choose one.

They're all asking the same underlying question: what kind of shopfloor systems do we want to run for the next ten years?

There are broadly four answers.

Online, this debate can get almost political, with very strong voices in every camp. It doesn't need to be confrontational. Different approaches suit different companies, and there are trade-offs whichever way you go.

I'll be upfront about my own position before I start. I work for a vendor of the fourth kind, and it's my preferred approach, particularly for manufacturers with multiple sites. I've tried to describe each approach the way its best advocates would.

## 1. Code it from scratch

**What it is.** Your own developers write a bespoke system in a general-purpose language, on your own database and infrastructure. Every screen, rule, report and interface is your code. This is the classic homegrown MES, and plenty of factories still run one.

**Where it works well:**

- **Complete control.** It does exactly what you want, in exactly the way you want, and you own the intellectual property.
- **No licence fees.** The developers' time is the main cost, which can look attractive at first.
- **Deep knowledge in-house.** The people who wrote it understand your process and your system inside out.
- **Quick to start.** A small team can have a first version running quickly, and AI coding tools make that faster than ever.

Manufacturers who start this way often outgrow it, or struggle with the medium and longer-term challenges it brings as the system grows and the people who built it move on. Building from scratch is a bit like building a kit car. It can be rewarding, as long as you have the right expertise. But you miss out on years of innovation from people who've done it many times before, and it usually ends up a bit rough around the edges, without any of the comforts and extras.

**What to watch:**

- **"Exactly what you want" depends on who builds it.** Code only gives you exactly what you want if your team is capable of building it. Many manufacturers don't have a software development team at all, and their core competence is manufacturing, not writing software.
- **AI doesn't remove the major challenges.** Large language models have made writing software far easier, and a first version can appear in days rather than months. But scalability, security, maintainability and dependence on the few people who understand the system all remain, for its whole life.
- **The longest road to value.** A system of any real scale takes years to build well, including the parts every factory needs, such as genealogy and audit trails.
- **People cost more than licences.** Hiring people full time to build and run it is expensive, and it gets more expensive over time as people leave and others have to take over.
- **No economies of scale or shared best practice.** A vendor spreads the cost of building and improving its product across many customers, and brings what it has learned from all of them into every release. A homegrown system carries the full cost on its own and starts without that experience, which is a big part of why it ends up so expensive.
- **The gaps are easy to miss.** Product teams spend years on user experience, performance at scale, security, industry best practice, standard KPIs such as ISO 22400, and how data should be stored and structured so you're ready for things like AI. An internal team can get some of the way quickly, but it's hard to match that depth and usability. The people building it are often not MES experts either.
- **You own everything, forever.** Security patches, operating system and database upgrades, documentation, testing and support all sit with you. Keeping it up to date is hard, so many homegrown systems stagnate, and risk becoming a security threat.
- **Key-person dependency is at its highest.** When the original developers leave, the knowledge often leaves with them. Towards the end of their life, I've seen many homegrown systems outsourced to try to maintain and improve them, and that's always expensive and a recipe for disaster.
- **It gets harder as you grow.** Add plants and the need to standardise, and custom code tends to multiply until the system is outgrown. It's a bit like a spreadsheet that grows over the years, as different people add their own ideas and changes, until it's such a tangle that nobody can use it properly and it slows you down instead of helping.

**A typical example:** a system written years ago by a small internal team, which still runs the plant and does its core job well. Few people understand how it works, change requests take months, and nobody wants to be the one who touches it.

We often go in and replace homegrown systems that have reached the end of their life: hard to use, no longer secure or performant, and often the person who built them has left. Replacing one is rarely simple, though. It's often expensive and time-consuming, and there's usually a lot of internal resistance, especially from the people who built it. The change management can be harder than implementing a proper solution would have been in the first place. More on what changes when you replace one in [Replacing a homegrown MES](/post/replacing-a-homegrown-mes).

## 2. Build from building blocks

**What it is.** You assemble your own applications on a toolkit made for builders: low-code app builders, IIoT and data tools, dashboards and some of your own code where needed. The toolkit handles the plumbing, so you're not starting from nothing, but it isn't a finished product. Your people design and build each application, then keep it running. In practice, each app usually solves one problem for one team, so the apps can end up behaving like point solutions that happen to share a toolkit.

**Where it works well:**

- **Much faster than coding.** Configuring something in a low-code environment is usually far quicker than building it from scratch, although AI coding tools are now closing that gap.
- **Flexible.** There's a lot of freedom in how you put the blocks together, although you still work within what the toolkit allows.
- **It empowers your own people.** Engineers can make changes themselves without waiting for a vendor, as they can with a good configurable platform.
- **Lower cost at first.** Licences for building-block tools often look modest, and a narrow use case, such as a dashboard or a digital checklist, can be live in weeks. But costs can grow over time, and the total cost of ownership can end up being very high.

You see this most in smaller companies with tech-savvy teams, and some of the toolkits in this space are doing very well.

**What to watch:**

- **Joining the blocks up correctly.** This is the biggest risk. You have the building blocks, but whether they're stitched together in the right way is down to whoever built them. You're relying on them having connected the right transactions and called the right things, and it gets complicated, especially for the people who pick the system up later.
- **App sprawl.** It's easy to go from one app to dozens, each built for a narrow use case by a different person. Before long you have app spaghetti: overlapping apps and no joined-up view of the operation.
- **You design some or all of the data model.** Context only exists if someone models it and keeps it consistent as the applications grow. Without that, each app holds its own version of orders, materials and machines, and connected, contextualised data is hard to come by.
- **Key-person dependency.** Knowledge sits with the people who built each app. When they move on, it goes with them. You can fall back on the vendor or a systems integrator if needed, but that goes against one of the main reasons for choosing this approach.

**A typical example:** a plant with a capable digital team builds a downtime tracking app, which proves useful. Later it builds another app for non-conformances, then one to manage replenishment and movements to the line. Over time the apps are disconnected from each other, even though they all sit on the same toolkit.

**Low-code isn't only for toolkits.** The best modern MES/MOM platforms include low-code tools of their own for screens, workflows and more. So you can build everything yourself on a low-code toolkit, or take a MES/MOM platform and configure it, building on it with the same kind of tools. The difference is how much is already built for you, on one connected data model, before you start.

## 3. Stitch together point solutions

**What it is.** You buy specific tools for each department or team and connect them: an OEE tool, a quality system, a CMMS, a connected worker app, a scheduling tool. Sometimes they're joined through a unified namespace (UNS), where each application publishes what it knows and subscribes to what it needs.

**Where it works well:**

- **Each team chooses.** Each department is able to select its own tool.
- **Quick wins, one area at a time.** You can start where the pain is biggest without committing to everything at once, although a modular MOM platform lets you grow into it over time too.
- **Freedom to swap.** If one tool disappoints, you can replace it without replacing everything, though you then have to redo the integrations.

**What to watch:**

- **Integration is the hard part.** Integrations between third-party systems work well when they're designed properly, and point-to-point is often the safest option. But each one is a significant part of the project, and needs an owner and retesting whenever either side upgrades. Getting the right people from every team aligned, and making sure each integration is designed correctly, is a big challenge in itself. You can end up with integration spaghetti across the landscape, and when several systems need updating at once, it gets messy.
- **A UNS isn't a shortcut.** It's a useful pattern for sharing live data, but not a silver bullet. The sender gets no confirmation that data arrived, so data can quietly fail to reach the systems that need it. It also only shows what's happening now, so you still need applications around it to add meaning and keep the history. You can't aggregate OEE from published figures, for example; you have to go back to the raw data. More in [What is a unified namespace (UNS)?](/post/unified-namespace-uns)
- **Context thins out between systems.** You can't pass all the context across every integration, so naturally you share a subset. The quality system knows a sample failed, but not necessarily what the machine was doing at the time.
- **Operators juggle applications.** Switching screens and logging in and out, losing context at each step. When something goes wrong, which system do they check first? I've seen people try to put a single front end over all the underlying applications, and I've never seen it work well. The applications underneath move on, the front end quickly falls out of date, and every change has to be made in several places at once.
- **Hard to scale.** When departments choose their own systems, it's usually happening at plant level, not enterprise level. Point solutions chosen that way usually struggle to scale across the landscape, which limits standardisation and benchmarking between sites.
- **Someone has to own the architecture.** Designing and governing the UNS structure, the data model, the integrations and the security around them is down to you.

**A typical example:** a site buys a strong OEE tool, a separate quality app and a connected worker tool, each chosen by a different team. Each works well on its own. The work, and most of the value, then sits in connecting them so that a failed check, the order that was running, the material lot and the operator's sign-off all line up.

## 4. Configure an out-of-the-box platform

**What it is.** You buy an MES/MOM platform that already covers production, quality, inventory, maintenance and more on one data model. You configure it to your processes rather than coding it, and your own teams build on top of it wherever you need something specific to your business. Most are modular, so you can start with one or two functions and switch on more as you go.

Done well, it's the best of all worlds. You get the freedom to build that draws people to coding or a toolkit, and the depth in each area that draws them to point solutions, without the inter-department integrations and long-term maintenance that come with either.

**Where it works well:**

- **The data is connected and contextualised from the start.** A downtime event, a quality result, a material consumption and an operator's sign-off all belong to the same order, in the same system.
- **Your teams build on a proper foundation.** The best platforms aren't only configurable. They come with low-code tools, so your own engineers can add screens, reports, workflows and whole applications without going back to the vendor. Everything they build sits on the platform's data model and infrastructure, so it's more secure, scales further, performs better and is far easier to maintain than an application built on its own. It also has the full context of every order and machine from the day it goes live.
- **No integrations between shopfloor functions.** Production, quality, inventory and maintenance share one platform, so nothing waits to be transferred. Operators get one login and one interface, and context stays intact as they move between tasks.
- **The vendor builds and maintains it.** Best practice from many factories, standard KPIs, upgrades, security and new capabilities such as AI all arrive through the roadmap, paid for across many customers.
- **Start small on the right path.** Begin with production or quality, then add inventory, logistics, maintenance, tooling or energy later without a new project to connect them.

**What to watch:**

- **Costs can look higher up front.** The whole scope and journey is evaluated at the start, so the total cost of ownership is more visible than with the other approaches. There are fewer indirect costs, but more direct ones. Expect the cost per site to start higher, then fall significantly as you roll out to more sites.
- **You adapt some processes.** You'll need to decide the mix: where you adapt to the system, and where the system adapts to you. Adapting isn't a bad thing. These systems are often built around best practice, so go into those conversations with an open mind.
- **Not every platform is truly configurable.** Some are really toolkits that need a lot of coding to fit together, or a number of acquired applications that aren't well integrated. Check how much is configuration and how much is customisation.
- **Integrations still need work.** Configuration reduces customisation, but rarely removes it entirely, especially for integrating equipment and third-party software.
- **You depend on a vendor.** Their roadmap and commercial health matter, so choose carefully. See [How to choose an MES](/post/how-to-choose-an-mes).

**A typical example:** a manufacturer goes live with production and quality on its first site, then switches on inventory and maintenance on the same platform the following year, without building an interface between them. Along the way, its own engineers build a few site-specific screens and workflows with the platform's low-code tools, rather than as separate applications.

## Side by side

| | Code from scratch | Build from blocks | Stitch point solutions | Configure a platform |
| --- | --- | --- | --- | --- |
| **Application fit** | Exact, if your team can build it | Close, within what the blocks allow | Good in each area | Good in each area |
| **Time to first value** | Longest | Fast for narrow use cases | Fast in each area, but slow overall | Moderate, then fast to extend |
| **Cost on day one** | Low licences, high effort | Lowest | Highest: separate purchases from each vendor | Often more than less capable options, but less than buying everything separately and stitching it together |
| **Cost over ten years** | Grows with every feature, fix and departure | Grows with every feature and departure | Grows with every interface and upgrade | Most predictable |
| **Connected, contextualised data** | Only if you design it | Only if you model it | Partly, across interfaces | Built in |
| **Integrations to maintain** | All of them, written by you | Yours, between everything you build | One per boundary | Mainly to ERP, other specialist applications, and equipment |
| **Upgrades and security** | All yours, down to the infrastructure | Depends on the toolkit | Spread across several vendors | Mostly the vendor's |
| **Building your own on top** | Everything is yours to build | Yes, within what the toolkit allows | Separately in each tool | Yes, on the platform's own tools and data |
| **Who you depend on** | A few developers | A few internal people | Several vendors, plus your integrators | One vendor, plus your internal team |

## Get the mix right

No single application does everything a manufacturer needs. ERP, MES/MOM, a WMS for complex warehousing, supply chain planning and PLM all have their place, and most manufacturers run several of them. The skill is in getting the mix right, and being deliberate about where the boundaries sit.

Draw those boundaries around business domains, such as finance, manufacturing, distribution and supply chain, rather than around departments. Splitting the shopfloor into separate systems for production, quality, inventory and maintenance puts boundaries right through the middle of the work, where people and data need to flow freely. ERP runs the business and its finances, MES/MOM runs manufacturing and a WMS runs complex distribution, each connected through well-designed interfaces.

Where something really is unique to you, build it on top of the platform, with its own tools and data, rather than as another separate system.

## How to decide

- What will each option cost over ten years, including your own people, not just the first quote?
- Who maintains it when the original team moves on?
- How much of the value depends on data from different functions lining up in real time?
- How many interfaces will you own, and who will monitor them?
- Is your manufacturing process really unique, or is it the business processes around it? See [Configure, don't customise](/post/configure-dont-customise).
- How will you add AI and new capabilities, and who will build them?

## My view

Personally, I like being part of a connected ecosystem. It's a bit like a phone, laptop and watch from the same ecosystem: everything works together, and it gets better over time.

I think a configurable platform that your teams can build on is the best of all worlds, and gives the most value over time, particularly for large, multi-site manufacturers. All the data is connected and in context from the moment it's captured. There are no integrations between shopfloor functions to build or maintain, and nothing waits to be transferred. And you're not building and maintaining it yourself for ten years. The vendor does that, across many customers.

Each of the other approaches can work for a while, and plenty of factories run well on them today. The challenges tend to arrive in the medium to long term, as you add sites and the applications multiply. That's when the gap between building everything yourself and building on a proper platform really shows.

Whichever you choose, start on the right path, with the destination in mind.

If you're already running a homegrown system, there's no shame in it. Many were written when the market had nothing suitable, and they've served their factories well.

Which of the four are you running on today, and is it the one you'd choose again?
