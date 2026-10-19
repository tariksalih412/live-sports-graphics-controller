# Development log

How the project was built, and the real problems met on the way. Newest first.

## Problems solved

| Date | Problem | Cause | Fix |
|---|---|---|---|
| 2026-10-18 | Youth match showed 0-0 at full time instead of 3-3; Latin name with digits shown as "München U19 1860" | Provider has no goal events for youth leagues, and the rebuild trusted events only; numbers inside a Latin name were reordered by the RTL row | Full time always shows the official result and a clear warning is printed; each team name keeps its own text direction |
| 2026-10-18 | Score looked reversed on screen (Real Betis 2-5 Barcelona read as Barcelona 2-5) | Right-to-left layout put the home team on the right, but the score was forced left-to-right | Score digits follow the row direction, so each number sits next to its team; alert sends both numbers |
| 2026-10-18 | Free API plan only returns matches inside a short date window | Plan limit | `rebuild_match.py`: one request per finished match, saved locally, replayed minute by minute |
| 2026-10-18 | Own goal shown with the wrong scorer | Goal player was taken from the team's last goal, not the new one | Pick the new goal event and credit own goals to the other side |
| 2026-10-18 | Missed penalty counted as a goal | Provider lists it as type `Goal`, detail `Missed Penalty` | Map it to a non-goal event |
| 2026-10-17 | `.venv` pushed to GitHub, wrong languages shown | No `.gitignore` at first commit | Added `.gitignore`, removed `.venv` from the index, amended the first commit |
| 2026-10-17 | pytest tried to run a CasparCG tool and failed | File name started with `test_` | `pytest.ini` limits tests to `tests/`; tool renamed `check_templates.py` |
| 2026-10-17 | `CG ADD` returned `404` although the template file existed | CasparCG's HTML engine (CEF) failed to start, so `.html` templates were unknown | Restart CasparCG with no leftover processes; check the log for `Failed to initialize CEF` |
| 2026-10-17 | CasparCG shut itself down at start | Port 5250 held by the mock engine left running | Found the process with `netstat -ano`, stopped it; never run both on one port |
| 2026-10-17 | Graphics would not fit the channel | Channel set to 720p, templates are 1920×1080 | `video-mode` set to `1080i5000` |

## Build phases

1. **TCP client and mock engine.** One connection to port 5250, keep-alive, reconnect with backoff, and a fake CasparCG to test against.
2. **Data model.** Pydantic models and a mapper from API-Football JSON; a replay feed for recorded snapshots.
3. **Change detection.** Only changes are sent: score, goal, card, clock, status. VAR reversals update the score with no alert.
4. **CasparCG templates.** HTML scorebug and event alert with `update()`, `play()` and `stop()`, Arabic right-to-left text, title-safe layout.
5. **Real data.** API helper, live recorder and finished-match rebuilder.
6. **Release.** Tests in CI, logging with a latency summary, documentation and demo.
