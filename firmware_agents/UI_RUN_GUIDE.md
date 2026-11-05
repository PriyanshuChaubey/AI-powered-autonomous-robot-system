# Run the presentation UI

## 1. Open the project folder
Open the `firmware_agents` folder in VS Code.

## 2. Install Streamlit
```bash
python -m pip install -r requirements-ui.txt
```

## 3. Start the webpage
```bash
streamlit run app.py
```
Streamlit will open the UI in your browser (usually http://localhost:8501).

## 4. Enter a mission
Type the user's robot task in the **Mission prompt** box and click **Run Agents 1–3**.

The UI shows:
- Agent 1: requirements, constraints and acceptance tests
- Agent 2: architecture and validated Arduino pin map
- Agent 3: generated Arduino firmware and lint result
- Downloadable JSON, reports and `.ino` sketch

## Execution modes
- **Mock / presentation demo:** offline, fast, deterministic. It uses fixed outputs in `mock_data.py`; the entered prompt is not used to generate new AI content. Use this to demonstrate the screen and pipeline contracts, and say honestly that it is mock mode.
- **Real LLM API:** uses the mission prompt with an OpenAI-compatible or Ollama-compatible endpoint. Configure the model, base URL and API key in the sidebar. Do not expose the API key on a projector or in screenshots.

## Where is the prompt in the original code?
The command-line pipeline reads `examples/mission.txt` by default. You can also pass a different text file:
```bash
python pipeline.py examples/mission.txt
```
In code, `pipeline.py` reads the mission file and passes its text to `agent1_requirements.run(...)`. Agent 1 calls `prompts.a1_user(mission, catalog)`. Agents 2 and 3 receive the previous agent's validated JSON output.

## Important code consistency note
The supplied project code and `hardware_catalog.json` target **Arduino Uno R3**. The current `examples/mission.txt` and parts of `README.md` still mention **ESP32**. Use the Arduino Uno mission shown by default in the UI unless you intentionally update the hardware catalog, prompts, validators and firmware target together. Do not mix ESP32 pin numbers with Arduino Uno.
