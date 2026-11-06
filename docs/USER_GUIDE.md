# SLT Bilingual Core: User Guide

## Getting Started
1. Run `install.bat` (Windows) or `install.sh` (Linux/macOS) to set up the environment.
2. Launch the application:
   ```bash
   .venv\Scripts\activate.bat
   python app.py
   ```
3. Position your hand clearly in front of the camera, approximately 40 to 90 cm away.

## Keyboard Shortcuts
| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **F1** | Toggle Guide | Open or close the sign guide drawer showing all 19 vocabulary postures |
| **F2** | Toggle Camera | Start or stop the camera video stream |
| **F3** | Toggle Pause | Pause or resume live gesture classification |
| **F4** / **Ctrl+L** | Clear Sentence | Empty the accumulated gloss buffer and reset subtitles |
| **F5** | Speak Spanish | Pronounce the current sentence in Spanish |
| **F6** | Speak English | Pronounce the current sentence in English |
| **F7** | Speak Both | Pronounce the Spanish sentence followed by the English translation |
| **Space** | Speak Active | Speak the sentence using the currently selected voice mode |
| **Backspace** | Undo Sign | Remove the last confirmed sign from the gloss sequence |
| **Ctrl+Q** | Quit | Safely close camera, speech workers, and exit the application |

## Performing Signs
- Hold each sign steady for ~0.3 seconds until it appears in the **Señas Confirmadas** buffer.
- Drop your hand slightly or relax your fingers to release the gesture before making the next sign.
- Press **F1** at any time to consult anatomical instructions for each sign.
