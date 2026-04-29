# Mobile Ticket: Help Center Topic Deep Linking

**Type:** Feature  
**Platform:** Mobile (iOS & Android)  
**Priority:** 🔴 High  
**Requested By:** Haneen Al Jabari (CRM Team)  
**Engineering Contact:** Abdullah Tariq, Muhammad Asif  

---

## User Story

**As a** Tamara customer receiving a push notification  
**I want** to be redirected to a specific Help Center topic/section when I tap the notification  
**So that** I can quickly access relevant help content (e.g., Security & Fraud Prevention) without manually navigating through the app

---

## Description

Currently, the Tamara mobile app does not support deep linking into specific Help Center topics or sections. The CRM team needs the ability to include deep links in push notifications that open a targeted Help Center section when the customer taps on the notification.

The immediate use case is directing customers to the **"Security & Fraud Prevention"** section (`topicId: 30WBviOMYBqdMVAP9pGNFd`) via push notifications, but the solution should be generic enough to support any Help Center topic.

### Deep Link Format

The deep link should follow the existing Go Link pattern:

**Staging:**
```
https://tamarastg.go.link/help-center/topic?topicId={topicId}&topicTitle={topicTitle}
```

**Example:**
```
https://tamarastg.go.link/help-center/topic?topicId=30WBviOMYBqdMVAP9pGNFd&topicTitle=Security%20%26%20Fraud%20Prevention
```

### End-to-End Flow

1. CRM team configures a push notification campaign with a Help Center deep link
2. Customer receives the push notification on their device
3. Customer taps the notification
4. The app opens and navigates directly to the specified Help Center topic/section
5. If the app is not installed, the link should fall back gracefully (e.g., open the web version at `support.tamara.co`)

### Reference

- Help Center web URL: `https://support.tamara.co/en-US/sections/30WBviOMYBqdMVAP9pGNFd`
- Help Center content is sourced from the Zendesk-powered `support.tamara.co`

---

## Acceptance Criteria

- [ ] The app supports deep linking to any Help Center topic via the `help-center/topic` route
- [ ] Deep link accepts `topicId` and `topicTitle` as query parameters
- [ ] Tapping a push notification containing a Help Center deep link opens the app and navigates to the correct topic section
- [ ] The Help Center topic screen loads the correct content matching the provided `topicId`
- [ ] The topic title displayed in the app matches the `topicTitle` parameter (URL-decoded)
- [ ] If the app is already open, the deep link navigates to the topic without restarting the app
- [ ] If the app is closed/killed, the deep link opens the app and navigates to the topic after launch
- [ ] Deep link works on both iOS and Android
- [ ] Staging deep link is validated end-to-end with the CRM team before production rollout
- [ ] Fallback behavior is handled gracefully if the topic is not found or the content fails to load (e.g., show an error state or redirect to the Help Center home)
- [ ] The deep link respects the user's language preference and loads the Help Center topic in the correct locale (Arabic or English)
- [ ] The deep link is provided to the CRM team in both staging and production formats for integration with push notification campaigns
