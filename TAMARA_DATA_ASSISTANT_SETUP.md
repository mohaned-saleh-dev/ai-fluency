# Tamara Data Assistant Setup Complete! 🎉

## What's Been Set Up

### 1. ✅ Directory Structure
- **Location**: `/Users/mohaned.saleh/tamara-data-assistant`
- **Main script**: `src/data-assistant.py`
- **Config**: `src/configs/config.json`

### 2. ✅ MCP Configuration
- **Config file**: `~/.config/cursor/mcp.json`
- **Server name**: `tamara-data-assistant`
- **Command**: `/Users/mohaned.saleh/.local/bin/uv`
- **Status**: Configured and ready

### 3. ⚠️ Remaining Steps

#### A. Install Google Cloud SDK (gcloud)
If gcloud is not installed, run:
```bash
# For macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL  # Restart your shell
```

Or download from: https://cloud.google.com/sdk/docs/install

#### B. Set Up gcloud Authentication
Once gcloud is installed, run:
```bash
# Initialize gcloud
gcloud init
# - Choose your Tamara account when prompted
# - Enter 'n' (not 'Y') when asked to set up default network
# - Choose 'tamara-44603' as the project

# Set up application default credentials
gcloud auth application-default login
```

#### C. Update Hatta Models Path (if needed)
The config currently points to: `/Users/mohaned.saleh/hatta/models`

If you have the hatta repo in a different location, update:
```bash
# Edit the config file
nano ~/tamara-data-assistant/src/configs/config.json
```

Update the `models_path` to point to your hatta repo's models directory.

#### D. Restart Cursor
After completing the above steps:
1. **Restart Cursor** to load the new MCP server configuration
2. Toggle the MCP tool on/off in Cursor settings to see the green indicator

## Testing

Once everything is set up, you can test by asking:
- "Query BigQuery for external disputes with status rejected in 2025"
- "Get columns from hatta_data_science.external_disputes table"
- "Scan query cost for [your query]"

## Troubleshooting

### If you get permission errors:
- Make sure gcloud is authenticated: `gcloud auth list`
- Verify project is set: `gcloud config get-value project`
- Should show: `tamara-44603`

### If MCP server doesn't start:
- Check that `uv` is installed: `which uv`
- Verify the path in `~/.config/cursor/mcp.json` is correct
- Check Cursor's MCP logs for errors

### If you get quota_exceeded errors:
- Delete GCP credential files
- Re-run `gcloud init` and `gcloud auth application-default login`

## Available Tools

Once set up, you'll have access to:
- `get_columns_of_a_table_in_gbq` - Get table schema
- `run_query` - Execute BigQuery queries
- `scan_query_cost` - Estimate query costs
- `compare_success_rates` - Statistical comparisons
- `query_gcloud_logs` - Query application logs
- `run_python_analysis` - Run Python code with BigQuery data
- `run_optbinning_analysis` - Optimal binning analysis












