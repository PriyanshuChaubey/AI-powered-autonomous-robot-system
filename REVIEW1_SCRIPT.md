# First Review — What to Show and What to Say

Total time: about 6 minutes. The rule throughout: **lead with the AI, show
the robot as the proof.**

---

## Before you walk in

Have these four windows open, in this order:

1. A terminal in `firmware_agents/`
2. `artifacts/pin_map_report.txt`
3. `artifacts/robot_controller/robot_controller.ino`
4. The Arduino IDE, with the sketch open and `ESP32 Dev Module` selected

Have the physical robot on the table, powered off. Do not hand it around until
the end.

Run `python3 pipeline.py` once beforehand so the artifacts exist, then clear the
screen. You want to run it live, not read old output.

---

## Slide 1 — The problem (30 s)

> "Our project builds an AI pipeline that turns a plain-English requirement into
> working, tested code. In the last review the panel told us to add a robotics
> component. We did — but not by bolting a robot onto the side. We made the
> robot the thing the AI has to program."

That sentence is the whole framing. Everything after it is evidence.

---

## Slide 2 — The five agents (45 s)

Point at the diagram and name them in order:

> "Five agents. Requirements, Architecture, Firmware, Testing, Review and Repair.
> Today we are showing the first three, working end to end, plus the physical
> robot they target."

Then the key line:

> "Agent 2 does not just design — it allocates physical ESP32 pins. And unlike a
> normal chatbot, it is not allowed to decide whether its own wiring is legal."

That is what makes this a research project and not a wrapper around an API.

---

## Live demo, part 1 — the happy path (90 s)

In the terminal:

```bash
python3 pipeline.py
```

While it runs, narrate:

> "Agent 1 reads the mission and produces testable requirements — six functional,
> five non-functional, five acceptance tests in Given-When-Then form.
>
> Agent 2 turns those into a component list, a power budget, a state machine and
> a pin map. Twelve signals on twelve ESP32 pins.
>
> Agent 3 writes the Arduino sketch. Then our linter checks it against the pin
> map Agent 2 produced."

It finishes in under a second in mock mode. When it ends:

```bash
cat artifacts/pin_map_report.txt
```

> "Every pin is decoded and checked. One warning: the status LED is on GPIO 2,
> which is a boot-strapping pin. It is safe for an LED and we accepted it, but
> the system flagged it rather than hiding it."

---

## Live demo, part 2 — the part they will remember (90 s)

This is the important one. Run:

```bash
python3 demo_validator_fail.py
```

Let it print, then point at each block:

> "We deliberately broke the design four ways — the mistakes a language model
> actually makes.
>
> One: it drives a motor from GPIO 34, which is input-only. Blocked.
>
> Two: it puts both IR sensors on the same pin. Blocked.
>
> Three: it picks GPIO 6, which is wired to the board's flash chip. Using it
> would crash the ESP32. Blocked.
>
> Four: it writes `delay(500)` into the control loop, which would freeze the
> robot for half a second. Blocked."

Then the line to finish on:

> "So the pipeline is not 'the AI wrote some code and we hoped'. Every stage is
> a gate. The model proposes, the validator disposes."

---

## Live demo, part 3 — the robot (60 s)

Open the generated sketch in the Arduino IDE.

> "This is the file the pipeline produced, unedited. It has never been
> hand-written."

Scroll to show the pin defines, then flash it.

With the serial monitor open at 115200:

> "Every control cycle prints one JSON line: state, distance, both IR flags.
> That line is the interface the Testing agent will use in the next phase — the
> robot reports what it actually did, and the Repair agent fixes the code from
> that."

Put the robot on the floor, let it drive, put your hand in front of it. It stops
and turns. Then:

> "That behaviour was not typed by us. It came out of Agent 3, against a pin map
> that Agent 2 proposed and our validator approved."

---

## What to say if they push back

**"Isn't this just calling ChatGPT?"**

> "A single call cannot do this. There are five stages with different
> responsibilities, structured JSON passed between them, a hardware rule engine
> that rejects illegal wiring, and a repair loop. If we swapped the model out
> tomorrow, the pipeline would still work. The model is one component, not the
> system."

**"The robot is basic — obstacle avoidance is a first-year project."**

> "The robot is deliberately simple, because it is the test-bed, not the
> contribution. Our contribution is that an AI writes its firmware and repairs
> it from what the hardware reports. A complex robot would add noise to that
> measurement, not value. The simple robot gives us a clean signal: did the
> generated code work on real hardware, yes or no."

**"What is new here that isn't in Code as Policies or ProgPrompt?"**

> "Those show an LLM can generate robot code. We are asking whether a
> *multi-agent* pipeline with an explicit hardware-validated contract between
> design and code generation produces fewer invalid programs and repairs its own
> failures faster than a single model doing both steps. That is an empirical
> question and we are measuring it."

**"Where is the actual AI? This looks like templates."**

> "Today's run is in mock mode — fixed outputs — so the demo cannot fail on
> stage. The real-model path is one environment variable away, and that is what
> we will show at the next review along with the first measurements. We chose to
> make the contracts and the validators solid before tuning prompts, because
> without them a model comparison means nothing."

Say that last part honestly. It is a stronger answer than pretending the mock
outputs are model output.

**"Is the hardware bought?"**

> "Not yet. The BOM is about ₹2,000, inside the ₹6,000 budget, and the proposal
> is with our guide. The code and the wiring plan are ready, so the build is
> two evenings once the parts arrive."

---

## The one-sentence close

> "We are not building a robot project with AI in it. We are building an AI
> system that programs a robot, and we can prove — pin by pin, rule by rule —
> that it refuses to produce code that would break it."
