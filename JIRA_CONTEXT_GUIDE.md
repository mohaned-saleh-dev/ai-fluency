# How Jira Context Works

## Overview

The PRD Ticket Agent uses Jira as a knowledge base to ensure consistency, proper terminology, and alignment with existing work when creating PRDs and tickets.

## What Jira Resources Are Accessed?

When creating a PRD or ticket, the agent automatically:

### 1. **Searches for Related Issues**
- Uses keywords from your project description
- Finds issues related to the topic/feature
- Extracts implementation details, dependencies, and patterns

### 2. **Fetches Recent Issues**
- Gets issues updated in the last 90 days (for PRDs)
- Gets issues updated in the last 60 days (for tickets)
- Provides general context and consistency patterns

### 3. **Extracts Knowledge Base**
- Analyzes all fetched issues
- Extracts:
  - **Technical components** in use
  - **Common terminology** and naming conventions
  - **Writing patterns** and issue formats
  - **System names** and architecture
  - **Labels and categories**

## How It Works - Step by Step

### When Creating a PRD:

```
1. User: "create prd for user authentication feature"
   ↓
2. Agent searches Jira:
   - Related issues → Finds issues about "user authentication"
   - Recent issues → Gets last 90 days of work
   - Project issues → Gets issues from active projects
   ↓
3. Agent extracts knowledge:
   - Technical components (e.g., "Auth Service", "User API")
   - Terminology (e.g., "customer" vs "user", "order" vs "transaction")
   - Writing patterns (how issues are described)
   - System architecture references
   ↓
4. Agent builds prompt with:
   - Your project description
   - Related Jira issues (for dependencies)
   - Jira knowledge base (for terminology and patterns)
   - Recent issues (for consistency)
   ↓
5. PRD is created with:
   - Correct technical terminology
   - Proper system references
   - Consistent with existing work
   - Aware of dependencies
```

### When Creating a Ticket:

```
1. User: "create ticket for login UI"
   ↓
2. Agent searches Jira:
   - Related issues → Based on PRD content + ticket description
   - Recent tickets → For format and style consistency
   ↓
3. Agent uses:
   - Similar ticket patterns
   - Technical system references
   - Acceptance criteria formats
   - User story patterns
   ↓
4. Ticket is generated with:
   - Consistent terminology
   - Proper technical references
   - Matching structure and style
```

## What Information Is Extracted?

### From Related Issues:
- Similar implementations
- Dependencies and related work
- Technical patterns and approaches
- Naming conventions

### From Recent Issues:
- Current work patterns
- Active technical systems
- Recent terminology
- Format consistency

### From Knowledge Base:
- **Technical Components**: System names, services, APIs
- **Terminology**: Correct terms used across issues
- **Labels**: Common categories and tags
- **Writing Patterns**: How issues are described
- **Architecture**: System relationships and dependencies

## Configuration

Your Jira credentials are already configured:
- **URL**: https://tamarapay.atlassian.net
- **Email**: mohaned.saleh@tamara.co
- **Token**: ✅ Configured

## What Gets Included in the Prompt

When you create a PRD, the prompt includes:

```
## Jira Knowledge Base
[Extracted knowledge from all scanned issues]
- Technical components: Auth Service, User API, Payment Gateway
- Common terminology: "customer" not "user", "order" not "transaction"
- Recent patterns: User stories follow "As a [role]..." format

## Related Jira Issues
[Issues directly related to your project]
- PROJ-123: User authentication implementation
- PROJ-456: Login flow redesign
...

## Recent Jira Issues (for consistency)
[Recent work for style consistency]
- PROJ-789: Recent feature implementation
...
```

## Benefits

✅ **Consistency**: Uses same terminology and patterns as existing issues
✅ **Context**: Understands dependencies and related work
✅ **Terminology**: Uses correct technical terms and system names
✅ **Patterns**: Matches writing style and format from existing tickets
✅ **Architecture**: Aware of technical systems and components

## Current Limitations

⚠️ **Search API**: Your Jira instance returns `410 Gone` for search endpoints
- This means the agent can't search by keywords automatically
- However, it can still:
  - Create tickets directly
  - Read specific issues (if you provide issue keys)
  - Use alternative methods for context

## Workarounds

If search doesn't work, you can:
1. **Provide issue keys** when creating tickets
2. **Use Notion context** (which is fully functional)
3. **Manually reference** Jira issues in your project description

The agent will still create high-quality PRDs and tickets using Notion context and any Jira information it can access.












