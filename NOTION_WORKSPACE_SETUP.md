# Notion Workspace Integration

## How It Works Now

The agent now scans your **entire Notion workspace** instead of specific pages. It will:

1. **Access the Agent workspace**: https://www.notion.so/tamaracom/Agent-13662429127880a291deebd5d0fdb130
2. **Extract knowledge from ALL documents** in that space:
   - OKRs
   - Projects
   - PRDs
   - Any other documents
3. **Use this comprehensive context** when creating PRDs and tickets

## What Gets Scanned

When you create a PRD, the agent will:

✅ **Extract knowledge base** from all pages in the workspace (up to 200 pages)
✅ **Search for OKRs** - Finds and includes OKR documents
✅ **Search for Projects** - Finds and includes project documents  
✅ **Search for PRDs** - Finds existing PRDs for format reference
✅ **Use all this context** in the generation prompt

## Configuration

The workspace ID is **already configured by default** to your Agent space:
- **Workspace ID**: `13662429127880a291deebd5d0fdb130`
- **URL**: https://www.notion.so/tamaracom/Agent-13662429127880a291deebd5d0fdb130

### To Use a Different Workspace

If you want to use a different Notion space, add to your `.env`:

```bash
NOTION_WORKSPACE_ID=your_workspace_page_id_here
```

## How to Get Workspace/Page ID

1. Open the Notion page/space in your browser
2. Click "..." menu → "Copy link"
3. Extract the ID from the URL:
   ```
   https://www.notion.so/tamaracom/Agent-13662429127880a291deebd5d0fdb130
                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                      This is the ID
   ```
4. Remove any hyphens if present

## What Information Is Used

The agent will use:

- **OKRs** → Strategic goals, objectives, key results
- **Projects** → Existing initiatives, dependencies, related work
- **PRDs** → Format, structure, tone, depth
- **All Documents** → General knowledge, terminology, conventions

## Benefits

✅ **Comprehensive Context** - Uses ALL documents, not just specific pages
✅ **Automatic Discovery** - Finds OKRs, projects, PRDs automatically
✅ **Up-to-date** - Always uses latest information from your workspace
✅ **No Manual Configuration** - Works out of the box with your Agent space

## Example: What Gets Included

When creating a PRD, the prompt will include:

```
## Workspace Knowledge Base
[All content from your workspace - OKRs, projects, PRDs, etc.]

## OKRs Context (X documents)
[Your OKR documents with objectives and key results]

## Projects Context (X documents)  
[Related project documents]

## Reference: Existing PRDs (X documents)
[PRD examples for format consistency]
```

The agent is now configured to use your entire Agent workspace automatically!












