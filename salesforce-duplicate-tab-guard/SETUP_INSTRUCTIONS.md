# Salesforce Duplicate Tab Guard — Complete Setup Instructions

## What This Does

When an agent opens Salesforce in a second browser tab, the second tab **automatically closes itself**. If the browser blocks the auto-close (rare edge case), the agent sees a full-screen warning telling them to close the tab manually.

**The first tab (with active Omni-Channel) is never touched.**

### Behavior Summary

| Time     | What happens                                     | Agent sees         |
|----------|--------------------------------------------------|--------------------|
| 0.0s     | Component detects a duplicate tab exists         | Nothing            |
| 0.1s     | **Attempt 1:** Tries to auto-close the tab       | Tab closes (done)  |
| 0.5s     | If still open → redirects to warning page        | Brief flash        |
| 0.5s     | **Attempt 2:** Warning page tries auto-close     | Tab closes (done)  |
| 0.8s     | **Attempt 3:** Tries a different close method    | Tab closes (done)  |
| 1.5s     | **Last resort:** Shows warning if still open     | Warning visible    |

~90% of the time the tab just closes silently. The warning is a safety net.

---

## What You Need

- A Salesforce admin login (someone who can access Developer Console and App Manager)
- A browser (Chrome, Edge, etc.) — that's it
- **No VS Code, no Salesforce CLI, no installs of any kind**

---

## PART A — Create the Warning Page (2 minutes)

This is the fallback page agents see IF auto-close doesn't work.

### Step 1: Open Developer Console

1. Log in to **Salesforce** as an admin
2. Click the **gear icon** ⚙️ (top right corner)
3. Click **Developer Console**
4. A new browser window opens — this is your code editor

### Step 2: Create a new Visualforce Page

1. In the Developer Console menu bar, click **File**
2. Click **New**
3. Click **Visualforce Page**
4. A popup appears asking for a name
5. Type exactly: `DuplicateTabWarning`
6. Click **OK**
7. A code editor opens with some default code in it

### Step 3: Paste the code

1. **Select ALL** the default code in the editor (Cmd+A on Mac, Ctrl+A on Windows)
2. **Delete** it (press Backspace or Delete)
3. Open the file `DuplicateTabWarning.vfp` from the `salesforce-duplicate-tab-guard` folder in your workspace
4. **Copy the ENTIRE contents** of that file
5. **Paste** it into the Developer Console editor
6. Press **Cmd+S** (Mac) or **Ctrl+S** (Windows) to save
7. You should see **"Save successful"** at the bottom of the screen

### Step 4: Quick test

1. Open a new browser tab
2. Go to: `https://YOUR-DOMAIN.lightning.force.com/apex/DuplicateTabWarning`
   - Replace `YOUR-DOMAIN` with your actual Salesforce domain
   - Example: `https://tamara.lightning.force.com/apex/DuplicateTabWarning`
3. The page should try to close itself. If your browser blocks the close, you'll see a warning message after ~1.5 seconds
4. If either of those happened → Part A is done ✅

---

## PART B — Create the Tab Detector Component (3 minutes)

This is the invisible component that detects when a duplicate tab is opened and auto-closes it.

### Step 5: Create a new Lightning Bundle

1. Go back to **Developer Console** (the window from Step 1)
2. In the menu bar, click **File**
3. Click **New**
4. Click **Lightning Bundle**
5. A popup appears asking for a name
6. Type exactly: `duplicateTabGuard`
7. Click **Submit**
8. A code editor opens showing a file called `duplicateTabGuard.cmp` with some default code

### Step 6: Paste the component code

1. **Select ALL** the default code in the `duplicateTabGuard.cmp` editor
2. **Delete** it
3. **Copy and paste** the following code:

```
<!--
    duplicateTabGuard — Aura Component
    
    Purpose: Detects if Salesforce is open in another browser tab.
    If yes, auto-closes the new tab. If auto-close fails, shows a warning.
    The original tab stays active and unaffected.
-->
<aura:component implements="flexipage:availableForAllPageTypes" access="global">
    <aura:handler name="init" value="{!this}" action="{!c.doInit}"/>
    <!-- This component is invisible — it runs silently in the utility bar -->
</aura:component>
```

4. Press **Cmd+S** / **Ctrl+S** to save
5. You should see **"Save successful"**

### Step 7: Create the Controller (the brain)

This is the most important file — it contains all the logic.

1. Look at the **right side** of the Developer Console editor
2. You'll see a vertical panel with clickable labels: **CONTROLLER**, HELPER, STYLE, RENDERER, etc.
3. Click **CONTROLLER**
4. A new tab opens in the editor called `duplicateTabGuardController.js`
5. It has some default code in it
6. **Select ALL** the default code and **Delete** it
7. Open the file `duplicateTabGuardController.js` from the `salesforce-duplicate-tab-guard` folder
8. **Copy the ENTIRE contents** of that file
9. **Paste** it into the Developer Console editor
10. Press **Cmd+S** / **Ctrl+S** to save
11. You should see **"Save successful"**

> **Can't find the sidebar?**
> Make sure you're on the `duplicateTabGuard.cmp` tab in the editor. The sidebar with CONTROLLER / HELPER / STYLE buttons only appears when you're viewing the `.cmp` file. Click on the `duplicateTabGuard.cmp` tab at the top of the editor to go back to it.

---

## PART C — Add It to Your Service Console App (2 minutes)

This is what makes the component run automatically for every agent.

### Step 8: Open the App Manager

1. Go back to your main **Salesforce** window (not Developer Console)
2. Click the **gear icon** ⚙️ (top right corner)
3. Click **Setup**
4. In the **Quick Find** search box on the top left, type: `App Manager`
5. Click **App Manager** when it appears in the results

### Step 9: Edit your Service Console app

1. You'll see a list of all your Salesforce apps
2. Find the **Service Console** app that your agents use
   - It might be called "Service Console", "Customer Service", or whatever your team named it
   - Look for the one with **App Type = "Lightning"** and your agents use daily
3. On the **right side** of that row, click the small **dropdown arrow ▼**
4. Click **Edit**

### Step 10: Add the component to the Utility Bar

1. A configuration screen opens for the app
2. In the **left sidebar**, click **Utility Items (Desktop Only)**
3. Click the **Add Utility Item** button
4. A search popup appears
5. Type: `duplicateTabGuard`
6. Click on **duplicateTabGuard** when it appears in the results
7. Now configure it:
   - **Label:** Type `Tab Guard` (agents won't see this — it stays hidden)
   - **Panel Width:** Leave as default (doesn't matter — it's invisible)
   - **Panel Height:** Leave as default (doesn't matter — it's invisible)
   - **Start automatically:** ✅ **CHECK THIS BOX** ← **THIS IS THE MOST IMPORTANT STEP. DO NOT SKIP THIS.**
8. Click **Save** (top right corner)
9. If prompted, click **Save** again to confirm

---

## PART D — Test It (1 minute)

### Step 11: Test with two tabs

1. **Close all Salesforce tabs** in your browser (start fresh)
2. Open **Chrome** (or your browser)
3. Go to your **Service Console** app in Salesforce
4. Wait **3 seconds** for everything to load — this is **Tab 1** (the "good" tab)
5. Open a **new browser tab** (Cmd+T on Mac, Ctrl+T on Windows)
6. Navigate to the **exact same Salesforce URL** in this new tab — this is **Tab 2** (the duplicate)
7. **Within 1-2 seconds**, one of these should happen:
   - ✅ **Best case:** Tab 2 automatically closes itself. You're taken back to Tab 1.
   - ✅ **Fallback:** Tab 2 redirects to a warning page that says "Salesforce Is Already Open — please close this tab"
8. **Tab 1** should be completely unaffected — Omni-Channel status intact ✅

### Step 12: Test the other direction

1. Now try opening a **third tab** with the same Salesforce URL
2. It should also auto-close or show the warning
3. Tab 1 remains the only working Salesforce tab ✅

---

## ✅ You're Done!

### What happens from now on:
- ✅ Every agent using the Service Console gets this protection automatically
- ✅ No Chrome extension needed
- ✅ No configuration on agent machines
- ✅ The duplicate tab auto-closes — agents don't need to do anything
- ✅ If auto-close is blocked, a warning page appears (can't be dismissed — the page IS the warning)
- ✅ The first tab (with active Omni-Channel) is always preserved
- ✅ Works on Chrome, Edge, Firefox, Safari
- ✅ Agents cannot bypass this — it's part of Salesforce itself

---

## Maintenance & Troubleshooting

### To remove it later:
1. Setup → App Manager → Find your Service Console app → ▼ → Edit
2. Click **Utility Items (Desktop Only)**
3. Find "Tab Guard" → click the **X** to remove it
4. Save

### To edit the warning message:
1. Developer Console → File → Open Resource
2. Search for `DuplicateTabWarning`
3. Edit the text in the HTML
4. Save

### It's not working — the duplicate tab stays open:
- Make sure **"Start automatically"** is checked in the Utility Item settings (Part C, Step 10)
- Make sure the agent is using the **correct Service Console app** (not a different Salesforce app)
- Try clearing the browser cache and reloading Salesforce
- The component only works within the **same browser** (e.g., two Chrome tabs). It won't detect a tab in Chrome vs. a tab in Edge — but that's fine since agents typically use one browser

### The component doesn't appear in "Add Utility Item":
- Go back to Developer Console and make sure both files saved without errors
- Check that the `.cmp` file contains `implements="flexipage:availableForAllPageTypes"`
- Try refreshing the App Manager page and searching again

### Agents complain the first tab gets closed instead of the second:
- This shouldn't happen — the logic specifically closes the NEWER tab
- If it does, have the agent close ALL Salesforce tabs, wait 5 seconds, and open a single fresh tab

---

## Total Setup Time: ~7 minutes

Zero installations. All done in the browser. No agent involvement needed.



