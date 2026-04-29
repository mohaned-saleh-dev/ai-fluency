# Chat Survey SDK — Ticket Breakdown

> **Epics:** (1) Reusable Chat Survey SDK, (2) Post-Support CSAT Survey (First Use Case)
>
> **Platform:** Flutter (iOS & Android)
>
> **Story Point Convention:** 3 SP = ~5 dev days including QA
>
> **Design Reference:** [Figma — Post-Support CSAT Chat Survey Flows](image attached)

---

## Context & Vision

The Chat Survey SDK is a **reusable, config-driven Flutter component** that renders conversational survey experiences inside the Tamara mobile app. It is designed to be:

- **Plug-and-play** — consuming teams drop in the widget and supply a survey configuration; no custom mobile development needed.
- **Survey-builder ready** — the configuration schema is designed so that a future survey builder UI can author and launch surveys without code changes.
- **Multi-use-case** — the same SDK powers post-support CSAT, NPS, in-app feedback, onboarding surveys, and any future conversational survey need.

The first use case is the **Post-Support Chat CSAT/ASAT Survey** shown in the attached design, which collects issue-resolution status, satisfaction rating (emoji scale), and optional free-text feedback after a customer support interaction.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   Host App (Tamara)                   │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │          Chat Survey SDK (Flutter Package)      │  │
│  │                                                │  │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  │  │
│  │  │ Chat UI  │  │  Survey   │  │  Message    │  │  │
│  │  │ Shell    │  │  Engine   │  │  Renderers  │  │  │
│  │  │          │  │ (Config → │  │  (Text,     │  │  │
│  │  │ Message  │  │  Flow     │  │  Quick      │  │  │
│  │  │ List +   │  │  Logic +  │  │  Reply,     │  │  │
│  │  │ Input    │  │  Branch)  │  │  Emoji,     │  │  │
│  │  │ Area     │  │           │  │  Multi,     │  │  │
│  │  │          │  │           │  │  FreeText,  │  │  │
│  │  │          │  │           │  │  CTA)       │  │  │
│  │  └──────────┘  └───────────┘  └────────────┘  │  │
│  │                                                │  │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  │  │
│  │  │ Theme    │  │ Analytics │  │ State      │  │  │
│  │  │ Engine   │  │ & Events  │  │ Manager    │  │  │
│  │  └──────────┘  └───────────┘  └────────────┘  │  │
│  │                                                │  │
│  │  ┌──────────────────────────────────────────┐  │  │
│  │  │       Public SDK API / Entry Point        │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ Survey Config│  │ Survey API   │                  │
│  │ (JSON/Remote)│  │ (Submit      │                  │
│  │              │  │  Responses)  │                  │
│  └──────────────┘  └──────────────┘                  │
└──────────────────────────────────────────────────────┘
```

---

## Survey Configuration Schema (Conceptual)

The SDK is driven by a JSON configuration that describes the entire survey flow. This is the contract that a future survey builder would produce.

```json
{
  "survey_id": "post_support_csat_v1",
  "version": "1.0.0",
  "locale": ["en", "ar"],
  "theme_id": "tamara_default",
  "entry_message": {
    "type": "text",
    "content": { "en": "Hi, How can we help?" }
  },
  "steps": [
    {
      "step_id": "issue_resolved",
      "type": "quick_reply",
      "bot_message": { "en": "Has your issue resolved?" },
      "options": [
        { "id": "yes", "label": { "en": "Yes" }, "next_step": "satisfaction" },
        { "id": "no", "label": { "en": "No" }, "next_step": "not_resolved_satisfaction" }
      ]
    },
    {
      "step_id": "satisfaction",
      "type": "emoji_rating",
      "bot_message": { "en": "How would you rate your experience?" },
      "scale": 5,
      "branching": {
        "1-2": "dissatisfied_feedback",
        "3": "neutral_feedback",
        "4-5": "satisfied_cta"
      }
    }
  ]
}
```

---

# Epic 1: Reusable Chat Survey SDK

> **Goal:** Deliver a production-ready, reusable Flutter SDK package that any team can use to render config-driven conversational surveys in-app.

---

## SDK-1: SDK Project Scaffolding & Chat UI Shell

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Set up the Flutter package project structure for the Chat Survey SDK and implement the foundational chat UI shell — the scrollable message list, bot avatar, message alignment (bot left, user right), and the overall conversation container. This is the skeleton that all message types plug into.

### Acceptance Criteria

- [ ] Flutter package created with proper folder structure (`lib/`, `src/`, `test/`, `example/`)
- [ ] `pubspec.yaml` configured with package metadata, no unnecessary dependencies
- [ ] `ChatSurveyWidget` — the root widget that takes a `SurveyConfig` and renders the chat shell
- [ ] Scrollable message list with auto-scroll-to-bottom on new messages
- [ ] Bot messages aligned left with configurable avatar
- [ ] User response messages aligned right with distinct styling
- [ ] Typing indicator animation (three-dot bounce) displayed before bot messages with configurable delay
- [ ] Message entrance animations (fade + slide-up)
- [ ] Empty state / loading state handled
- [ ] RTL layout support (Arabic)
- [ ] Unit tests for widget rendering and scroll behavior
- [ ] Example app within the package that renders a hardcoded conversation

### Technical Notes

- Use a `ListView.builder` with a message model list for performance
- The widget should accept a `ChatSurveyController` for programmatic control (start, reset, dispose)
- Keep the package dependency-lean; avoid pulling in heavy state management libraries — use `ChangeNotifier` or `ValueNotifier` patterns
- All text must go through a localisation delegate (no hardcoded strings)

### Design Reference

The overall chat container visible in all screens of the design: dark header area, white message area, message bubbles with rounded corners, bot avatar (green headset icon).

---

## SDK-2: Survey Configuration Model & Parser

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Define the Dart data models for the survey configuration schema and implement the parser that converts JSON config into strongly-typed Dart objects. This config drives the entire survey flow. The schema must be extensible for future message types and branching logic while remaining simple for basic use cases.

### Acceptance Criteria

- [ ] `SurveyConfig` root model containing metadata (survey_id, version, locale, theme_id) and a list of `SurveyStep` objects
- [ ] `SurveyStep` base class with subclasses for each step type:
  - `TextMessageStep` — bot sends a plain text message, auto-advances
  - `QuickReplyStep` — bot message + single-select button options
  - `EmojiRatingStep` — bot message + emoji scale (configurable 3/5 point)
  - `MultiSelectStep` — bot message + checkbox options with "Submit" CTA
  - `FreeTextStep` — bot message + text input field with "Submit" CTA
  - `CTAStep` — bot message + action button (deep link, app store, dismiss)
- [ ] Each step has: `step_id`, `bot_message` (localised), `next_step` (default), optional `branching` rules
- [ ] `BranchingRule` model: maps response values to `next_step` IDs
- [ ] `SurveyConfigParser.fromJson(Map<String, dynamic>)` factory with validation
- [ ] Validation: detect missing step_ids, circular references, unreachable steps
- [ ] Parsing errors surfaced via `SurveyConfigError` with human-readable messages
- [ ] Unit tests covering: valid config parsing, all step types, branching rules, validation errors, malformed JSON handling
- [ ] `toJson()` serialisation for each model (for future builder)

### Technical Notes

- Use `freezed` or manual immutable classes (discuss with team preference)
- The config can come from: hardcoded Dart, local JSON asset, or remote API. The parser should be source-agnostic.
- Keep the schema versioned (`version` field) for backward compatibility when a survey builder exists
- Branching rules should support: exact match, range match (for numeric scales), and default fallback

### Future Consideration (Survey Builder)

The schema is designed so that a survey builder UI can produce this JSON. Keep field names descriptive and avoid internal implementation details leaking into the config.

---

## SDK-3: Survey Flow Engine (State Machine & Branching)

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Implement the core survey engine that processes the `SurveyConfig`, manages the conversation state, handles user responses, evaluates branching rules, and drives the message list forward. This is the "brain" of the SDK — it decides which step comes next based on user input.

### Acceptance Criteria

- [ ] `SurveyEngine` class that takes a `SurveyConfig` and exposes a stream of `ChatMessage` objects
- [ ] State machine with states: `idle`, `running`, `waiting_for_input`, `completed`, `error`
- [ ] On start: engine emits the entry message, then the first step's bot message with its input component
- [ ] On user response: engine records the answer, evaluates branching rules, determines next step, emits next bot message(s) with typing delay
- [ ] Branching evaluation: exact match first, then range match, then default `next_step`
- [ ] Terminal steps (no `next_step` and no branching) transition engine to `completed`
- [ ] `SurveyResponse` model accumulates all step responses: `{ step_id, response_type, response_value, timestamp }`
- [ ] Engine exposes `onComplete` callback with the full `SurveyResponse` list
- [ ] Engine exposes `onStepCompleted` callback for per-step analytics hooks
- [ ] Configurable typing delay between bot messages (default 800ms–1200ms randomised for natural feel)
- [ ] `reset()` method to restart the survey from the beginning
- [ ] Unit tests covering: linear flow, branching (all paths), terminal step detection, reset, error handling for invalid step references

### Technical Notes

- Use a `Stream<List<ChatMessage>>` pattern so the UI reactively rebuilds as messages are added
- `ChatMessage` is a sealed class / union: `BotTextMessage`, `BotInputMessage`, `UserResponseMessage`, `TypingIndicatorMessage`
- The engine should be purely logic — no Flutter dependency — so it can be unit-tested without widget testing
- Avoid `async` for branching logic; only the typing delay should be async

---

## SDK-4: Message Renderers — Text & Quick Reply

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Implement the Flutter widget renderers for the two most fundamental message types: **Text Messages** (bot and user) and **Quick Reply** (single-select buttons). These appear in every survey flow.

### Acceptance Criteria

**Text Message Renderer:**
- [ ] `BotTextBubble` widget: rounded bubble, left-aligned, bot avatar, supports multiline text
- [ ] `UserTextBubble` widget: rounded bubble, right-aligned, distinct color, shows the user's selected response
- [ ] Both support RTL text direction
- [ ] Text supports basic formatting (bold via markdown-light) — optional, nice-to-have
- [ ] Entrance animation (fade + slide from bottom, 200ms)

**Quick Reply Renderer:**
- [ ] `QuickReplyInput` widget: renders a list of tappable pill/chip buttons below the bot message
- [ ] Each button shows the option label text
- [ ] Single-select behavior: tapping one disables all others
- [ ] Selected state: highlighted with distinct color (filled vs outlined)
- [ ] After selection: buttons become non-interactive, selected option appears as a `UserTextBubble`
- [ ] Buttons wrap to multiple rows if they don't fit in a single row
- [ ] Disabled state styling for after-selection
- [ ] RTL layout support
- [ ] Widget tests for: rendering, tap interaction, selection state, disabled state

### Design Reference

- Bot text bubbles: dark/grey background with white text, rounded corners
- User response bubbles: lighter/white background, right-aligned
- Quick reply buttons: visible in the "Has your issue resolved?" step with "Yes"/"No" style pills and in initial option selection screens

---

## SDK-5: Message Renderers — Emoji Rating Scale

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Implement the emoji-based satisfaction rating renderer. This is a core component visible in the Satisfied, Neutral, and Dissatisfied flows. It shows a row of emoji faces (5-point scale) that the user taps to rate their experience.

### Acceptance Criteria

- [ ] `EmojiRatingInput` widget: renders a horizontal row of emoji options
- [ ] Supports configurable scale sizes (3-point and 5-point)
- [ ] 5-point scale emojis: Very Dissatisfied (red angry), Dissatisfied (orange sad), Neutral (yellow meh), Satisfied (green smile), Very Satisfied (dark green star-eyes)
- [ ] Each emoji is a tappable circular button with the emoji icon and optional label beneath
- [ ] Tap feedback: selected emoji scales up slightly, unselected ones dim/shrink
- [ ] After selection: the rating is locked, selected emoji highlighted, row becomes non-interactive
- [ ] User response message appears showing the selected rating as text (e.g., "Satisfied" or the emoji itself)
- [ ] Emojis are custom SVG/vector assets bundled in the SDK package (not platform emoji for consistency)
- [ ] Horizontal scroll or wrap if screen width is too narrow (small devices)
- [ ] RTL layout: emoji order remains LTR (worst→best) but overall layout respects RTL
- [ ] Accessibility: each emoji has a semantic label for screen readers
- [ ] Widget tests for: rendering all scales, tap selection, locked state, accessibility labels

### Design Reference

The emoji rating row visible in the design across Satisfied, Neutral, and Dissatisfied paths. Also visible as standalone emoji icons at bottom-right of the design (red, orange, yellow, light green, dark green circles).

---

## SDK-6: Message Renderers — Multi-Select & Free Text Input

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Implement the remaining two input-type message renderers: **Multi-Select** (checkbox list) and **Free Text Input**. Multi-Select is used in the "Dissatisfied" flow for collecting specific feedback reasons. Free Text is used for open-ended "anything else?" feedback.

### Acceptance Criteria

**Multi-Select Renderer:**
- [ ] `MultiSelectInput` widget: renders a vertical list of checkbox options with labels
- [ ] Multiple options can be selected/deselected simultaneously
- [ ] Each option shows a checkbox (empty → checked) with label text
- [ ] "Submit" / "Done" button at the bottom, enabled only when at least one option is selected
- [ ] After submit: options become non-interactive, selected options appear as a `UserTextBubble` (comma-separated or list)
- [ ] Scrollable if options exceed visible area
- [ ] RTL support for text and checkbox alignment

**Free Text Input Renderer:**
- [ ] `FreeTextInput` widget: renders a text field with placeholder text and a "Submit" / "Send" button
- [ ] Multi-line text field with configurable max lines (default 4) and character limit
- [ ] "Submit" button enabled only when input is non-empty (after trimming whitespace)
- [ ] After submit: text field becomes non-interactive, user's text appears as a `UserTextBubble`
- [ ] Keyboard opens automatically when this step is reached (configurable)
- [ ] "Skip" option if the step is marked as optional in config
- [ ] RTL text input support
- [ ] Widget tests for: multi-select toggle, submit enablement, free text validation, skip behavior

### Design Reference

- Multi-select: visible in the "Dissatisfied" path — multiple feedback reason checkboxes shown in a dark-themed card
- Free text: visible as the text input field with keyboard in the Dissatisfied flow (the last screen before submission)

---

## SDK-7: Message Renderer — CTA Button & Survey Completion

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Implement the **CTA (Call-to-Action) button** renderer and the **survey completion** state. The CTA button is used for actions like "Rate on App Store", "Contact Support", or any deep link. Survey completion handles the end-of-survey state, submission trigger, and thank-you message.

### Acceptance Criteria

**CTA Button Renderer:**
- [ ] `CTAButtonInput` widget: renders a prominent action button (full-width or auto-width based on config)
- [ ] CTA actions supported: `deep_link` (opens URL), `app_store_review` (triggers in-app review), `dismiss` (closes survey), `custom` (fires callback to host app)
- [ ] Button styling: primary (filled, brand color) and secondary (outlined) variants
- [ ] After tap: button shows brief loading state, then fires the action
- [ ] If the CTA is a terminal action (e.g., dismiss), it triggers survey completion
- [ ] Optional "Skip" / "No thanks" secondary text link beneath the CTA

**Survey Completion:**
- [ ] When the engine reaches a terminal step (or CTA dismiss), a completion message is shown
- [ ] Completion message: configurable thank-you text (e.g., "Thank you for your feedback!")
- [ ] Animated checkmark or success indicator
- [ ] `onComplete` callback fires with the accumulated `SurveyResponse` list
- [ ] After completion, the chat becomes read-only (scrollable but no interactions)
- [ ] Auto-dismiss option: survey container dismisses after configurable delay (e.g., 3 seconds)
- [ ] Widget tests for: CTA rendering, action firing, completion state, auto-dismiss

### Design Reference

- CTA button: visible in the "Satisfied" flow — "Rate on App Store" button (purple, full-width)
- Completion: the final screen in each flow showing a confirmation state

---

## SDK-8: Theming Engine & Customisation API

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Implement the theming engine that allows consuming teams to customise the visual appearance of the chat survey without modifying SDK code. This ensures the SDK can match different brand contexts and survey moods.

### Acceptance Criteria

- [ ] `ChatSurveyTheme` class with all customisable tokens:
  - **Colors:** primary, secondary, background, surface, botBubbleColor, userBubbleColor, botTextColor, userTextColor, accentColor, errorColor
  - **Typography:** fontFamily, botMessageStyle, userMessageStyle, buttonTextStyle, headerStyle
  - **Shapes:** bubbleBorderRadius, buttonBorderRadius, inputBorderRadius
  - **Spacing:** messagePadding, bubblePadding, avatarSize, typingIndicatorSize
  - **Assets:** botAvatarWidget (allows custom avatar), emojiAssets (allows custom emoji set)
- [ ] `ChatSurveyTheme.tamara()` — default Tamara brand theme matching the design
- [ ] `ChatSurveyTheme.light()` and `ChatSurveyTheme.dark()` — generic presets
- [ ] Theme is passed via the `ChatSurveyWidget` constructor or inherited via `ChatSurveyThemeProvider`
- [ ] All renderers (SDK-4 through SDK-7) consume theme tokens — no hardcoded colors/styles
- [ ] Theme hot-reload works during development
- [ ] RTL-aware spacing and alignment (theme doesn't break in Arabic)
- [ ] Unit tests: theme application, fallback to defaults, custom theme override
- [ ] Document all theme tokens with descriptions in code comments

### Technical Notes

- Model after Flutter's `ThemeData` pattern — `ChatSurveyTheme.copyWith()` for partial overrides
- Keep the theme serialisable (JSON ↔ Dart) for future remote theming via survey builder

---

## SDK-9: Analytics Event Hooks & Response Submission Interface

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Implement the analytics and event hooks layer, plus the response submission interface. The SDK should fire well-defined events throughout the survey lifecycle that consuming teams can listen to for tracking. The submission interface defines how survey responses are sent to the backend without coupling the SDK to a specific API.

### Acceptance Criteria

**Analytics Events:**
- [ ] `SurveyEventListener` abstract interface with the following event callbacks:
  - `onSurveyStarted(surveyId, metadata)`
  - `onStepDisplayed(surveyId, stepId, stepType)`
  - `onStepAnswered(surveyId, stepId, responseValue, responseTimeMs)`
  - `onSurveyCompleted(surveyId, responses, totalDurationMs)`
  - `onSurveyDismissed(surveyId, lastStepId, reason)` — reason: user_closed, timeout, error
  - `onSurveyError(surveyId, errorType, errorMessage)`
  - `onCTATapped(surveyId, stepId, actionType, actionTarget)`
- [ ] Each event includes timestamp and session context
- [ ] Multiple listeners can be registered (e.g., one for Mixpanel, one for internal analytics)
- [ ] Events are fire-and-forget (never block the survey flow)

**Response Submission:**
- [ ] `SurveySubmitter` abstract interface: `Future<bool> submit(SurveyResult result)`
- [ ] `SurveyResult` model: `{ surveyId, responses[], startedAt, completedAt, metadata }` where metadata includes interaction_id, customer_id, etc.
- [ ] SDK calls `submit()` on completion; host app provides the implementation
- [ ] Built-in `HttpSurveySubmitter` that POSTs to a configurable URL (for teams that want zero-config submission)
- [ ] Retry logic: configurable retry count (default 3) with exponential backoff on failure
- [ ] Offline queue: if submission fails, queue locally and retry on next app launch (using lightweight local storage)
- [ ] `onSubmissionSuccess` and `onSubmissionFailure` callbacks
- [ ] Unit tests for: event emission ordering, submission retry, offline queue

### Technical Notes

- The `SurveySubmitter` is injected via the `ChatSurveyWidget` constructor — dependency inversion keeps the SDK decoupled from any specific backend
- For the offline queue, use `shared_preferences` or a simple file-based queue — avoid adding SQLite as a dependency

---

## SDK-10: Localisation (AR/EN) & Accessibility

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Implement full Arabic/English localisation for all SDK-internal strings and ensure WCAG 2.1 AA accessibility compliance across all components.

### Acceptance Criteria

**Localisation:**
- [ ] All SDK-internal strings (typing indicator label, "Skip", "Submit", "Send", error messages) are localised in AR and EN
- [ ] Survey config content (bot messages, option labels) is localised via the config's locale map — SDK renders the correct locale based on app locale
- [ ] RTL layout fully functional: message alignment, text direction, button order, scroll direction
- [ ] Number formatting respects locale (Arabic-Indic numerals if applicable)
- [ ] Date/time formatting respects locale
- [ ] Locale can be overridden at the widget level (for testing or forced locale scenarios)
- [ ] If a locale is missing from config, fall back to first available locale with a console warning

**Accessibility:**
- [ ] All interactive elements have semantic labels (`Semantics` widget)
- [ ] Emoji rating: each emoji announces its meaning (e.g., "Very Satisfied, 5 of 5")
- [ ] Quick reply buttons announce their label and selected state
- [ ] Multi-select checkboxes announce checked/unchecked state
- [ ] Free text input has a clear accessible label and hint
- [ ] Focus traversal order follows logical conversation flow (top to bottom)
- [ ] Sufficient color contrast ratios (4.5:1 for text, 3:1 for UI elements)
- [ ] Support for large text / dynamic type scaling (up to 200%)
- [ ] Screen reader announcement when new bot message appears
- [ ] Test with TalkBack (Android) and VoiceOver (iOS)
- [ ] Accessibility test cases documented and passing

### Technical Notes

- Use Flutter's `Localizations` and `LocalizationsDelegate` pattern
- Bundle `.arb` files within the SDK package for internal strings
- Test with `flutter test --accessibility` and manual screen reader testing

---

## SDK-11: SDK Public API, Documentation & Example App

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Define and polish the public API surface of the SDK, write developer documentation, and build a comprehensive example app that demonstrates all features. This is the "developer experience" ticket — it determines how easy it is for other teams to adopt the SDK.

### Acceptance Criteria

**Public API:**
- [ ] Single entry point: `ChatSurveyWidget` with a clean constructor:
  ```dart
  ChatSurveyWidget({
    required SurveyConfig config,
    ChatSurveyTheme? theme,
    SurveySubmitter? submitter,
    List<SurveyEventListener>? eventListeners,
    Locale? locale,
    VoidCallback? onDismiss,
    Duration typingDelay,
  })
  ```
- [ ] `ChatSurveyController` for programmatic control: `start()`, `reset()`, `dispose()`, `currentState` getter
- [ ] `SurveyConfig.fromJson()` and `SurveyConfig.fromAsset(String path)` factory methods
- [ ] All public classes and methods have dartdoc comments
- [ ] No internal implementation details exposed (barrel file exports only public API)
- [ ] Semantic versioning ready — `CHANGELOG.md` started

**Documentation:**
- [ ] `README.md` with: installation, quick start (< 10 lines to render a survey), configuration guide
- [ ] API reference generated via `dart doc`
- [ ] "Survey Config Schema" reference document explaining each step type, branching, and locale fields
- [ ] "Theming Guide" showing how to customise colors, fonts, and assets
- [ ] "Integration Guide" for connecting to a backend (SurveySubmitter implementation)
- [ ] Migration guide placeholder (for future breaking changes)

**Example App:**
- [ ] Standalone Flutter app in `example/` directory
- [ ] Demonstrates: all message types, branching flows, both AR and EN, theme customisation, analytics logging to console, mock submission
- [ ] Multiple survey configs included as JSON assets (simple linear, branching, all-input-types)
- [ ] Runs on both iOS and Android simulators

---

## SDK-12: SDK Integration Testing & QA Hardening

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Comprehensive integration testing of the full SDK: end-to-end survey flows, edge cases, performance, and device compatibility.

### Acceptance Criteria

**Integration Tests:**
- [ ] End-to-end flow test: start survey → answer all steps → completion callback fires with correct responses
- [ ] Branching flow test: verify all branch paths produce correct message sequences
- [ ] Mid-survey dismiss: verify `onSurveyDismissed` fires with correct last step
- [ ] Locale switching: start in EN, verify AR renders correctly (and vice versa)
- [ ] Theme override: verify custom theme applies to all renderers
- [ ] Rapid tapping: verify no double-submission or state corruption on quick taps
- [ ] Keyboard handling: free text input with keyboard open, then dismiss, verify layout is correct
- [ ] Scroll behavior: long conversation (10+ messages) scrolls correctly, auto-scroll on new message
- [ ] Empty config: verify graceful error, not a crash
- [ ] Network failure on submit: verify retry and offline queue
- [ ] Memory: no memory leaks on repeated start/dispose cycles

**Device Compatibility:**
- [ ] iPhone SE (small screen) — layout doesn't overflow
- [ ] iPhone 15 Pro Max (large screen) — layout looks proportional
- [ ] Android (Pixel 7, Samsung Galaxy S23) — renders correctly
- [ ] Tablet — survey is usable (not stretched)

**Performance:**
- [ ] Survey load time < 100ms (from config parse to first message rendered)
- [ ] Message rendering < 16ms per frame (no jank during animations)
- [ ] Memory footprint < 20MB for a 20-message conversation

---

# Epic 2: Post-Support CSAT Survey (First Use Case)

> **Goal:** Using the Chat Survey SDK, implement the specific post-support CSAT survey shown in the design. This includes the survey configuration, trigger logic, and integration with the existing chat/support infrastructure.

---

## CSAT-1: Post-Support CSAT Survey Configuration

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Author the full survey configuration JSON for the Post-Support CSAT flow shown in the design. This is the first real config that exercises the SDK's branching, all input types, and multi-path logic.

### Acceptance Criteria

- [ ] Survey config JSON covers the complete flow from the design:

  **Entry:**
  - Bot: "Hi, How can we help?" (contextual greeting)
  - Bot: Summary of support interaction (dynamic, injected via metadata)

  **Step 1 — Issue Resolution:**
  - Bot: "Has your issue been resolved?"
  - Quick Reply: "Yes" / "No"
  - Branch: Yes → Step 2a (Resolved Satisfaction) | No → Step 2b (Unresolved Satisfaction)

  **Step 2a — Resolved Satisfaction:**
  - Bot: "Great! How would you rate your experience?"
  - Emoji Rating (5-point)
  - Branch: 4–5 (Satisfied) → Step 3a | 3 (Neutral) → Step 3b | 1–2 (Dissatisfied) → Step 3c

  **Step 2b — Unresolved Satisfaction:**
  - Bot: "We're sorry to hear that. How would you rate your overall experience?"
  - Emoji Rating (5-point)
  - Branch: 4–5 → Step 3a-unresolved | 3 → Step 3b | 1–2 → Step 3c

  **Step 3a — Satisfied Path:**
  - Bot: "Would you rate the app on the App Store?"
  - Quick Reply: "Yes, I'd love to!" / "Maybe later"
  - If yes → CTA: "Rate on App Store" (deep link to app store)
  - Bot: "Thank you for your feedback!" → Survey Complete

  **Step 3a-unresolved — Satisfied but Unresolved:**
  - Bot: "We're going to transfer you to an agent to help you."
  - Bot: "In the meantime, would you rate the app?"
  - CTA: "Rate on App Store"
  - Survey continues to agent handoff

  **Step 3b — Neutral Path:**
  - Bot: "Can you tell us what we could improve?"
  - Multi-Select: options from design (e.g., "Response time", "Accuracy of help", "Ease of use", "Friendliness", "Other")
  - Bot: "Would you like to add anything else?"
  - Free Text (optional, skippable)
  - Bot: "Thank you for your feedback!" → Survey Complete

  **Step 3c — Dissatisfied Path:**
  - Bot: "We're sorry about your experience. What went wrong?"
  - Multi-Select: dissatisfaction reasons (e.g., "Issue not resolved", "Long wait time", "Unhelpful response", "Rude interaction", "Confusing process", "Other")
  - Bot: "Is there anything else you'd like to tell us?"
  - Free Text (optional, skippable)
  - Bot: "Thank you. We'll use your feedback to improve." → Survey Complete

- [ ] Config authored in both EN and AR
- [ ] Config validated against SDK schema (no errors from parser)
- [ ] Config stored as a versioned JSON asset in the app
- [ ] Config includes metadata fields for: `interaction_id`, `agent_id`, `interaction_type` (chatbot/agent), `chat_topic`
- [ ] Branching logic tested against all paths using the SDK's unit test framework

### Technical Notes

- The dynamic content (interaction summary) is injected at runtime via a `metadata` map passed to `ChatSurveyWidget`
- The survey config should be loadable from both local asset and remote endpoint (for future A/B testing)
- Coordinate with content/copywriting team for final AR translations

---

## CSAT-2: Survey Trigger Service & Suppression Rules

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Implement the service that detects when a support chat interaction ends and triggers the CSAT survey. Includes suppression logic to prevent survey fatigue.

### Acceptance Criteria

**Trigger Logic:**
- [ ] Listen for `chat_ended` events from the existing chat service (both chatbot-resolved and agent-ended)
- [ ] On `chat_ended`: check suppression rules → if eligible, display survey
- [ ] Survey appears as a bottom sheet overlay sliding up from the bottom of the chat screen
- [ ] Configurable delay before survey appears (default: 2 seconds after chat ends)
- [ ] If user navigates away before delay completes, cancel the trigger
- [ ] Survey trigger works for both chatbot interactions and live agent interactions

**Suppression Rules:**
- [ ] No duplicate survey for the same `interaction_id`
- [ ] Maximum one survey per user per 24-hour rolling window
- [ ] Configurable global suppress flag (kill switch via remote config)
- [ ] Configurable per-chat-topic suppression (e.g., don't survey for "password reset" topics)
- [ ] Suppression state persisted locally (survives app restart within the window)

**Edge Cases:**
- [ ] App killed during survey → survey is lost (no zombie survey on next launch)
- [ ] Multiple chats in rapid succession → only the first triggers a survey within the 24h window
- [ ] Chat service event not received (fallback) → survey does not appear (fail-safe: no survey is better than a broken survey)

- [ ] Unit tests for: suppression logic, trigger timing, edge cases
- [ ] Integration test: mock chat_ended event → verify survey widget appears

---

## CSAT-3: Host App Integration & Bottom Sheet Presentation

**Type:** Story | **Points:** 3 | **Priority:** P0

### Description

Integrate the Chat Survey SDK into the Tamara host app. Implement the bottom sheet presentation layer, connect the survey trigger service, wire up the survey submitter to the existing Survey API (UFME), and connect analytics events.

### Acceptance Criteria

**Bottom Sheet Integration:**
- [ ] Survey renders in a modal bottom sheet (`showModalBottomSheet`) over the chat screen
- [ ] Bottom sheet height: 85% of screen height (configurable)
- [ ] Dismissible via swipe-down gesture and X button in header
- [ ] Bottom sheet has rounded top corners matching design
- [ ] Background dim overlay behind the bottom sheet
- [ ] Keyboard-aware: bottom sheet adjusts when keyboard opens for free text input

**API Integration:**
- [ ] `SurveySubmitter` implementation that posts to the existing Survey API endpoint (CSSV-2033)
- [ ] Payload maps `SurveyResult` to the API contract: `survey_type` (CSAT/ASAT), `interaction_id`, `customer_id`, `response_value`, `channel: "in-app"`
- [ ] Differentiate CSAT (chatbot) vs ASAT (agent-assisted) based on `interaction_type` from chat metadata
- [ ] Auth token passed from host app session
- [ ] Error handling: API failure → show subtle error toast, queue for retry

**Analytics Wiring:**
- [ ] `SurveyEventListener` implementation that fires events to the app's existing analytics pipeline (Mixpanel/internal)
- [ ] Events mapped to standard event taxonomy
- [ ] All events include: `customer_id`, `interaction_id`, `interaction_type`, `market`, `app_version`

**Feature Flag:**
- [ ] Survey feature gated behind a remote config flag: `chat_survey_enabled`
- [ ] Separate flags for chatbot vs agent survey if needed

- [ ] QA: end-to-end test on staging environment (trigger chat → complete survey → verify data in Survey API)

---

## CSAT-4: Dynamic Content Injection & Agent Handoff

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Implement the dynamic content injection mechanism that personalises the survey (interaction summary, agent name) and the agent handoff flow for the "Issue Not Resolved" path.

### Acceptance Criteria

**Dynamic Content:**
- [ ] Survey config supports template variables in bot messages: `{{agent_name}}`, `{{chat_topic}}`, `{{interaction_summary}}`
- [ ] Template variables resolved at runtime from the `metadata` map passed to the SDK
- [ ] If a variable is missing, fall back to a generic message (no raw `{{variable}}` shown to user)
- [ ] Entry message dynamically shows the support topic the user chatted about

**Agent Handoff (Unresolved + Satisfied Path):**
- [ ] When the user indicates their issue is not resolved, the survey flow includes a step that offers to connect them to a live agent
- [ ] "Transfer to agent" CTA button triggers a callback to the host app
- [ ] Host app handles the actual agent routing (via existing chat service)
- [ ] Survey completion is still recorded even if agent handoff is initiated
- [ ] If the user is already in an agent chat, skip the handoff offer

- [ ] Unit tests for: template resolution, missing variable fallback, handoff callback
- [ ] Integration test with mock chat context

---

## CSAT-5: End-to-End QA, UAT & Launch Readiness

**Type:** Story | **Points:** 3 | **Priority:** P1

### Description

Final QA pass, UAT sign-off, and launch readiness checklist for the Post-Support CSAT Survey.

### Acceptance Criteria

**QA Test Matrix:**
- [ ] All survey paths tested (Resolved/Unresolved × Satisfied/Neutral/Dissatisfied = 6 paths)
- [ ] AR and EN tested for all paths
- [ ] RTL layout verified on all screens
- [ ] iOS (iPhone SE, iPhone 15 Pro) tested
- [ ] Android (Pixel, Samsung) tested
- [ ] Dark mode tested (if applicable)
- [ ] Accessibility: VoiceOver (iOS) and TalkBack (Android) tested for one full flow each
- [ ] Slow network: survey submission with 3G simulation
- [ ] Offline: survey completion while offline → submission on reconnect
- [ ] Survey suppression: verify 24h window, duplicate interaction_id block
- [ ] Analytics: verify all events fire correctly in staging analytics dashboard
- [ ] API: verify survey responses appear correctly in Survey API / UFME

**UAT:**
- [ ] Product owner sign-off on all 6 paths (screen recordings)
- [ ] Copywriting review of all AR and EN text
- [ ] Design review of visual fidelity vs Figma

**Launch Readiness:**
- [ ] Feature flag tested: ON shows survey, OFF hides survey
- [ ] Rollback plan documented: disable feature flag
- [ ] Monitoring: alert set up for survey submission failure rate > 5%
- [ ] Runbook: what to do if survey blocks chat flow (kill switch procedure)
- [ ] Release notes drafted

---

# Ticket Dependency Graph

```
SDK-1 (Chat UI Shell) ─────────┐
                                │
SDK-2 (Config Model) ──────────┼──▶ SDK-3 (Survey Engine) ──┐
                                │                            │
                                │    SDK-4 (Text + Quick     │
                                │          Reply) ───────────┤
                                │                            │
                                │    SDK-5 (Emoji Rating) ───┤
                                │                            │
                                │    SDK-6 (Multi-Select +   │
                                │          Free Text) ───────┤
                                │                            │
                                │    SDK-7 (CTA + Complete) ─┤
                                │                            │
SDK-8 (Theming) ────────────────┼────────────────────────────┤
                                │                            │
SDK-9 (Analytics + Submit) ─────┤                            │
                                │                            │
SDK-10 (i18n + a11y) ──────────┤                            │
                                │                            │
SDK-11 (Public API + Docs) ─────┼──▶ SDK-12 (Integration ───┘
                                │           Testing)
                                │              │
                                │              ▼
                                │     CSAT-1 (Survey Config) ─┐
                                │                             │
                                │     CSAT-2 (Trigger +       │
                                │            Suppress) ───────┤
                                │                             │
                                │     CSAT-3 (Host App        │
                                │            Integration) ────┤
                                │                             │
                                │     CSAT-4 (Dynamic Content │
                                │            + Handoff) ──────┤
                                │                             │
                                │     CSAT-5 (E2E QA +        │
                                │            Launch) ─────────┘
                                │
```

**Parallelisation Notes:**
- SDK-1 and SDK-2 can start in parallel (day 1)
- SDK-4, SDK-5, SDK-6, SDK-7 can all be parallelised once SDK-1 shell is ready
- SDK-8 and SDK-9 can start once SDK-1 is available
- SDK-3 depends on SDK-2 (needs the config model)
- SDK-10 can start alongside SDK-4–7 (retrofitting a11y as renderers are built)
- SDK-11 and SDK-12 are integration/polish tickets — later in the timeline
- CSAT-1 through CSAT-5 depend on the SDK being substantially complete (SDK-1 through SDK-9 minimum)

---

# Summary

| Epic | Tickets | Total Story Points | Estimated Dev Days |
|------|---------|--------------------|--------------------|
| **Chat Survey SDK (Reusable)** | SDK-1 through SDK-12 | 36 SP | 60 days |
| **Post-Support CSAT Survey** | CSAT-1 through CSAT-5 | 15 SP | 25 days |
| **Total** | **17 tickets** | **51 SP** | **85 days** |

> With 2 developers working in parallel (leveraging the parallelisation notes above), the SDK epic can be delivered in ~6-7 weeks, and the CSAT use case in ~3 weeks after SDK stabilises, for a total of ~9-10 weeks wall-clock time.

---

# Future Considerations (Survey Builder)

The SDK is explicitly designed to support a future **Survey Builder** tool:

1. **Config-driven:** All survey logic lives in the JSON config, not in code. A builder UI just needs to produce valid JSON.
2. **Schema versioned:** The `version` field in configs allows backward-compatible evolution.
3. **Extensible step types:** New message types can be added by registering a renderer + step type without modifying existing code.
4. **Remote config:** Configs can be fetched from an API endpoint, enabling live survey updates without app releases.
5. **Theming via tokens:** Themes can be stored and applied remotely, allowing brand-per-survey customisation.
6. **Analytics abstraction:** Any backend can receive events by implementing the listener interface.

When the survey builder is built, the workflow becomes:
```
Product Manager → Survey Builder UI → JSON Config → API → SDK fetches config → Renders survey
```

No mobile development required for new surveys.
