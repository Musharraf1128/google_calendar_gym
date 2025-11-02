# UI Realism Test Report

**Test Date:** 2025-11-03 00:42:07

**UI_REALISM:** `true`

## Features Tested

### 1. Random Popup Overlays

The following popup types are randomly displayed (30% chance per render):

- **reminder_toast**: Toast notification - Meeting reminder
- **event_edit_modal**: Modal dialog - Edit event form with Save button
- **permission_error**: Error banner - Permission denied warning
- **event_created_toast**: Success toast - Event created confirmation
- **sync_notification**: Info indicator - Syncing status
- **calendar_shared_toast**: Info toast - Calendar shared notification
- **invitation_popup**: Dialog - Meeting invitation with Accept/Decline

### 2. Scroll Offset Variation

- Random vertical offset: ±10px (±0.02 in normalized coordinates)
- Simulates user scrolling behavior
- Makes each screenshot slightly different even for same state

### 3. Event Color Randomization

Events are assigned random colors from Google Calendar's official palette:

1. Lavender (#7986cb)
2. Sage (#33b679)
3. Grape (#8e24aa)
4. Flamingo (#e67c73)
5. Banana (#f6c026)
6. Tangerine (#f5511d)
7. Peacock (#039be5)
8. Graphite (#616161)
9. Blueberry (#3f51b5)
10. Basil (#0b8043)
11. Tomato (#d60000)

### 4. Popup Diversity Index

- Tracks unique popup types shown across episode
- Calculated as: `unique_popups / total_popup_types`
- Displayed in screenshot title when UI_REALISM=true
- Range: 0.0 (no popups) to 1.0 (all 7 popup types shown)

## Generated Screenshots

Total screenshots: **16**

All screenshots saved to: `gym_screenshots_realism/`

1. `realism_demo_00_reset.png`
2. `realism_demo_01_event_1.png`
3. `realism_demo_02_event_2.png`
4. `realism_demo_03_event_3.png`
5. `realism_demo_04_event_4.png`
6. `realism_demo_05_rerender_0.png`
7. `realism_demo_06_rerender_1.png`
8. `realism_demo_07_rerender_2.png`
9. `realism_demo_08_rerender_3.png`
10. `realism_demo_09_rerender_4.png`
11. `realism_demo_10_rerender_5.png`
12. `realism_demo_11_rerender_6.png`
13. `realism_demo_12_rerender_7.png`
14. `realism_demo_13_rerender_8.png`
15. `realism_demo_14_rerender_9.png`
16. `realism_demo_15_rerender_10.png`

## Key Observations

1. **Visual Diversity**: Each screenshot may show different popups, creating realistic UI distractions
2. **RL Training Value**: Agents must learn to focus on calendar state despite UI noise
3. **Scroll Variations**: Subtle position changes simulate real user behavior
4. **Color Consistency**: Each event maintains its assigned color throughout episode
5. **Production-like UX**: Popups use Google Calendar's design language and colors

## Configuration

To enable UI realism features, set in `.env`:

```bash
UI_REALISM=true
```

To disable (for clean screenshots):

```bash
UI_REALISM=false
```

## Example Popup Types

- **reminder_toast**: Top-right toast with dark background and bell icon
- **event_edit_modal**: Center modal with semi-transparent backdrop overlay
- **permission_error**: Full-width red banner at top of screen
- **event_created_toast**: Bottom-center green success notification
- **sync_notification**: Top-left blue indicator with sync icon
- **calendar_shared_toast**: Bottom-right blue info toast
- **invitation_popup**: Right-side dialog with Accept/Decline buttons

## Conclusion

The UI realism features successfully simulate real-world calendar interactions, providing a more challenging and realistic environment for RL agent training. The popup diversity index helps track the variety of UI distractions encountered during training episodes.
