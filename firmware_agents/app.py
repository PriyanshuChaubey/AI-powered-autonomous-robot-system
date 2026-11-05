from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent1_requirements
import agent2_architecture
import agent3_firmware
from llm import LLMClient

st.set_page_config(
    page_title="Autonomous Robot | AI Agent Demo",
    page_icon="🤖",
    layout="wide",
)

st.markdown("""
<style>
.main {background: #f7f9fc;}
.block-container {padding-top: 1.5rem; max-width: 1400px;}
.hero {padding: 1.3rem 1.5rem; border-radius: 16px; color: white;
       background: linear-gradient(120deg,#102a43,#176b87);}
.hero h1 {color:white; margin:0 0 .3rem 0;}
.hero p {color:#e5f4fa; margin:0;}
.agent-card {padding: 1rem; border:1px solid #dbe4ee; border-radius:12px;
             background:white; margin-bottom:.5rem;}
.small-muted {color:#61758a; font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🤖 AI-Powered Autonomous Robot System</h1>
  <p>Five-agent engineering workflow · Live demonstration of Agents 1–3</p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.info(
    "Enter a robot mission below. The current code runs Agent 1 (requirements), "
    "Agent 2 (hardware architecture and pin validation), and Agent 3 "
    "(Arduino firmware generation and linting) in sequence."
)

DEFAULT_MISSION = (
    "Develop a two-wheel autonomous robot using an Arduino Uno R3. "
    "It should move forward, measure nearby obstacles using an HC-SR04 "
    "ultrasonic sensor mounted on an MG995 servo, and stop safely when an "
    "obstacle is too close. Use an L298N motor driver and two DC geared motors. "
    "Generate Arduino-compatible firmware and include safe motor-stop behaviour."
)

with st.sidebar:
    st.header("Run configuration")
    run_mode = st.radio(
        "Execution mode",
        ["Mock / presentation demo", "Real LLM API"],
        help="Mock mode uses fixed example outputs from mock_data.py. Real mode calls the configured model.",
    )
    st.caption("Target board is fixed in the supplied project code: Arduino Uno R3.")
    if run_mode == "Real LLM API":
        provider = st.selectbox("API format", ["OpenAI-compatible", "Ollama-compatible"])
        model = st.text_input("Model name", value="gpt-4o-mini" if provider == "OpenAI-compatible" else "llama3.1")
        base_url = st.text_input(
            "Base URL",
            value="https://api.openai.com/v1" if provider == "OpenAI-compatible" else "http://localhost:11434/v1",
        )
        api_key = st.text_input(
            "API key" if provider == "OpenAI-compatible" else "API key (optional)",
            type="password",
            help="Used only for this run; do not share or display your key during the presentation.",
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
    else:
        provider, model, base_url, api_key, temperature = "Mock", "golden-example", "", "", 0.2

st.subheader("1. Enter the user's robot mission")
mission = st.text_area(
    "Mission prompt",
    value=DEFAULT_MISSION,
    height=150,
    placeholder="Example: Build a robot that follows a path and avoids obstacles...",
)
st.caption("This text is passed directly to Agent 1. Agents 2 and 3 receive the validated outputs of the previous agent.")

run_clicked = st.button("▶ Run Agents 1–3", type="primary", use_container_width=True)

def show_json(title: str, data: dict):
    st.download_button(
        f"Download {title} JSON",
        data=json.dumps(data, indent=2),
        file_name=title.lower().replace(" ", "_") + ".json",
        mime="application/json",
        key=f"download_{title}",
    )
    st.json(data, expanded=False)

if run_clicked:
    if not mission.strip():
        st.error("Please enter a mission prompt.")
        st.stop()

    catalog_path = HERE / "hardware_catalog.json"
    if not catalog_path.exists():
        st.error("hardware_catalog.json was not found beside app.py.")
        st.stop()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE / "artifacts" / "ui_runs" / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    if run_mode == "Mock / presentation demo":
        llm = LLMClient(
            mode="mock",
            base_url="",
            model="golden-example",
            api_key="",
            temperature=0.2,
        )
        mode_label = "MOCK MODE — fixed sample outputs"
    else:
        if provider == "OpenAI-compatible" and not api_key.strip():
            st.error("Enter an API key for the OpenAI-compatible endpoint.")
            st.stop()
        llm = LLMClient(
            mode="openai" if provider == "OpenAI-compatible" else "ollama",
            base_url=base_url.strip().rstrip("/"),
            model=model.strip(),
            api_key=api_key.strip(),
            temperature=temperature,
        )
        mode_label = f"REAL MODEL — {model}"

    st.markdown(f"**Execution:** `{mode_label}`")
    progress = st.progress(0, text="Starting pipeline...")
    try:
        with st.spinner("Agent 1 is analysing the mission..."):
            req = agent1_requirements.run(
                mission, catalog, llm, out_dir / "1_requirements.json"
            )
        progress.progress(33, text="Agent 1 complete — requirements validated")

        with st.spinner("Agent 2 is designing the architecture and validating pins..."):
            arch = agent2_architecture.run(
                req,
                catalog,
                llm,
                str(out_dir / "2_architecture.json"),
                check_report_path=str(out_dir / "pin_map_report.txt"),
            )
        progress.progress(66, text="Agent 2 complete — architecture and pin map validated")

        with st.spinner("Agent 3 is generating firmware and running lint checks..."):
            fw = agent3_firmware.run(
                arch,
                llm,
                out_dir,
                lint_report_path=out_dir / "firmware_lint_report.txt",
            )
        progress.progress(100, text="All three agents completed")

        sketch_path = out_dir / "robot_controller" / "robot_controller.ino"
        sketch = sketch_path.read_text(encoding="utf-8") if sketch_path.exists() else ""
        st.session_state["last_run"] = {
            "mission": mission,
            "mode": mode_label,
            "requirements": req,
            "architecture": arch,
            "firmware": fw,
            "sketch": sketch,
            "out_dir": str(out_dir),
        }
        st.success("Agents 1–3 completed successfully. Review the outputs below.")
    except Exception as exc:
        progress.empty()
        st.error(f"Pipeline stopped: {type(exc).__name__}: {exc}")
        st.warning(
            "A later agent only runs if the previous agent's output passes validation. "
            "Check the project artifacts and the error shown above."
        )

result = st.session_state.get("last_run")
if result:
    st.divider()
    st.subheader("2. Agent outputs")
    st.caption(f"Last successful run: {result['mode']} · Saved in `{result['out_dir']}`")

    tabs = st.tabs([
        "Agent 1 · Requirements",
        "Agent 2 · Architecture",
        "Agent 3 · Firmware",
        "Generated files",
    ])

    with tabs[0]:
        req = result["requirements"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Functional requirements", len(req.get("functional_requirements", [])))
        c2.metric("Non-functional requirements", len(req.get("non_functional_requirements", [])))
        c3.metric("Acceptance tests", len(req.get("acceptance_tests", [])))
        st.markdown("**What Agent 1 did:** converted the user's plain-language mission into structured, testable requirements.")
        show_json("Agent 1 Requirements", req)

    with tabs[1]:
        arch = result["architecture"]
        c1, c2 = st.columns(2)
        c1.metric("Pin assignments", len(arch.get("pin_map", [])))
        c2.metric("Pin-map status", arch.get("_meta", {}).get("pin_map_status", "unknown").upper())
        st.markdown("**What Agent 2 did:** selected interfaces, prepared the pin map and checked it against the Arduino Uno hardware catalog.")
        pin_rows = []
        for item in arch.get("pin_map", []):
            pin_rows.append({
                "Signal": item.get("signal", ""),
                "Arduino pin": item.get("gpio", item.get("pin", "")),
                "Direction": item.get("direction", item.get("mode", "")),
                "Connected to": item.get("connected_to", ""),
            })
        if pin_rows:
            st.markdown("**Pin map**")
            st.dataframe(pin_rows, use_container_width=True, hide_index=True)
        show_json("Agent 2 Architecture", arch)

    with tabs[2]:
        fw = result["firmware"]
        meta = fw.get("_meta", {})
        st.markdown("**What Agent 3 did:** generated Arduino firmware from Agent 2's validated architecture and checked the code against the approved pin map.")
        st.metric("Firmware lint status", str(meta.get("lint_status", "see report")).upper())
        if result["sketch"]:
            st.code(result["sketch"], language="cpp")
            st.download_button(
                "⬇ Download Arduino .ino sketch",
                data=result["sketch"],
                file_name="robot_controller.ino",
                mime="text/plain",
            )
        show_json("Agent 3 Firmware Metadata", fw)

    with tabs[3]:
        out = Path(result["out_dir"])
        for filename in [
            "1_requirements.json",
            "2_architecture.json",
            "pin_map_report.txt",
            "firmware.json",
            "firmware_lint_report.txt",
        ]:
            path = out / filename
            if path.exists():
                st.download_button(
                    f"Download {filename}",
                    data=path.read_bytes(),
                    file_name=filename,
                    key=f"file_{filename}",
                )
        lint_path = out / "firmware_lint_report.txt"
        if lint_path.exists():
            st.markdown("**Firmware lint report**")
            st.code(lint_path.read_text(encoding="utf-8"))

st.divider()
st.markdown("""
**Presentation note:** The supplied code currently implements Agents 1–3 only.
Agent 4 (Testing & Validation) and Agent 5 (Review & Repair) are shown in the
architecture as planned stages, not as completed UI outputs.
""")
st.caption(
    "Important: Mock mode returns fixed golden examples from mock_data.py; it demonstrates the pipeline contracts and UI, "
    "not live AI reasoning. Use Real LLM API mode when you want the entered prompt to influence generated outputs."
)
