#!/usr/bin/env python3
"""
Extract all messages and threads from a specific Slack channel for the last N days.
Supports xoxc- session tokens with d cookie authentication.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()


def create_slack_client() -> WebClient:
    """Create a Slack WebClient with the appropriate authentication."""
    token = os.getenv("SLACK_XOXC_TOKEN") or os.getenv("SLACK_USER_TOKEN") or os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("Error: No Slack token found. Set SLACK_XOXC_TOKEN, SLACK_USER_TOKEN, or SLACK_BOT_TOKEN in .env")
        sys.exit(1)

    headers = {}
    if token.startswith("xoxc-"):
        d_cookie = os.getenv("SLACK_D_COOKIE")
        if not d_cookie:
            print("Error: xoxc- tokens require the SLACK_D_COOKIE value. Set it in .env")
            sys.exit(1)
        headers["cookie"] = f"d={d_cookie}"

    client = WebClient(token=token, headers=headers)

    try:
        auth = client.auth_test()
        print(f"Authenticated as: {auth['user']} (workspace: {auth['team']})")
    except SlackApiError as e:
        print(f"Authentication failed: {e.response.get('error', str(e))}")
        sys.exit(1)

    return client


def list_channels(client: WebClient) -> List[Dict]:
    """List all channels the authenticated user is a member of."""
    channels = []
    cursor = None

    while True:
        try:
            resp = client.users_conversations(
                types="public_channel,private_channel",
                exclude_archived=True,
                cursor=cursor,
                limit=200,
            )
            channels.extend(resp["channels"])
            next_cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not next_cursor:
                break
            cursor = next_cursor
        except SlackApiError as e:
            print(f"Warning: could not list channels: {e.response.get('error')}")
            break

    channels.sort(key=lambda c: c.get("name", ""))
    return channels


def resolve_users(client: WebClient, user_ids: set) -> Dict[str, str]:
    """Resolve user IDs to display names."""
    user_map = {}
    for uid in user_ids:
        if uid in user_map:
            continue
        try:
            resp = client.users_info(user=uid)
            user = resp["user"]
            user_map[uid] = user.get("real_name") or user.get("name") or uid
        except SlackApiError:
            user_map[uid] = uid
    return user_map


def extract_channel_messages(
    client: WebClient,
    channel_id: str,
    days_back: int = 30,
    include_threads: bool = True,
) -> List[Dict[str, Any]]:
    """Extract all messages from a channel for the last N days, including thread replies."""
    import time

    cutoff = datetime.now() - timedelta(days=days_back)
    oldest = str(int(cutoff.timestamp()))
    messages = []
    thread_tss = []
    cursor = None
    page = 0

    print(f"Fetching messages from the last {days_back} days...")

    while True:
        page += 1
        try:
            resp = client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                cursor=cursor,
                limit=200,
            )
        except SlackApiError as e:
            if e.response.get("error") == "ratelimited":
                delay = int(e.response.headers.get("Retry-After", 10))
                print(f"  Rate limited, waiting {delay}s...")
                time.sleep(delay)
                continue
            print(f"Error fetching history: {e.response.get('error')}")
            break

        batch = resp.get("messages", [])
        print(f"  Page {page}: {len(batch)} messages (total: {len(messages) + len(batch)})")

        for msg in batch:
            reply_count = msg.get("reply_count", 0)
            entry = {
                "ts": msg.get("ts"),
                "user": msg.get("user", msg.get("bot_id", "unknown")),
                "text": msg.get("text", ""),
                "type": msg.get("subtype", "message"),
                "reply_count": reply_count,
                "reactions": [
                    {"name": r["name"], "count": r["count"]}
                    for r in msg.get("reactions", [])
                ],
                "files": [
                    {"name": f.get("name"), "url": f.get("url_private")}
                    for f in msg.get("files", [])
                ],
                "thread_replies": [],
            }
            messages.append(entry)
            if include_threads and reply_count > 0:
                thread_tss.append(msg["ts"])

        next_cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not next_cursor or not resp.get("has_more"):
            break
        cursor = next_cursor
        time.sleep(0.2)

    print(f"Fetched {len(messages)} top-level messages.")

    if include_threads and thread_tss:
        print(f"Fetching replies for {len(thread_tss)} threads...")
        msg_index = {m["ts"]: m for m in messages}

        for i, tts in enumerate(thread_tss, 1):
            if i % 10 == 0 or i == 1 or i == len(thread_tss):
                print(f"  Thread {i}/{len(thread_tss)}...")
            try:
                replies = fetch_thread_replies(client, channel_id, tts)
                if tts in msg_index:
                    msg_index[tts]["thread_replies"] = replies
            except Exception:
                pass
            time.sleep(0.4)

    messages.sort(key=lambda m: float(m["ts"]))
    total_replies = sum(len(m.get("thread_replies", [])) for m in messages)
    print(f"Done: {len(messages)} messages + {total_replies} thread replies")
    return messages


def fetch_thread_replies(
    client: WebClient, channel_id: str, thread_ts: str
) -> List[Dict[str, Any]]:
    """Fetch all replies in a thread."""
    replies = []
    cursor = None

    while True:
        try:
            resp = client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                cursor=cursor,
                limit=200,
            )
        except SlackApiError:
            break

        for msg in resp.get("messages", []):
            if msg.get("ts") == thread_ts:
                continue
            replies.append({
                "ts": msg.get("ts"),
                "user": msg.get("user", msg.get("bot_id", "unknown")),
                "text": msg.get("text", ""),
                "reactions": [
                    {"name": r["name"], "count": r["count"]}
                    for r in msg.get("reactions", [])
                ],
            })

        next_cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not next_cursor or not resp.get("has_more"):
            break
        cursor = next_cursor

    return replies


def save_output(data: Dict, output_path: str):
    """Save extracted data to JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Saved to {output_path} ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Extract Slack channel conversations")
    parser.add_argument("--list", action="store_true", help="List available channels")
    parser.add_argument("--channel", type=str, help="Channel name or ID to extract")
    parser.add_argument("--days", type=int, default=30, help="Days of history (default: 30)")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--no-threads", action="store_true", help="Skip fetching thread replies")
    args = parser.parse_args()

    client = create_slack_client()

    if args.list:
        channels = list_channels(client)
        print(f"\n{'#':<4} {'Channel Name':<40} {'Members':<8} {'ID'}")
        print("-" * 80)
        for i, ch in enumerate(channels, 1):
            name = ch.get("name", "?")
            members = ch.get("num_members", "?")
            cid = ch["id"]
            print(f"{i:<4} #{name:<39} {members:<8} {cid}")
        print(f"\nTotal: {len(channels)} channels")
        return

    if not args.channel:
        print("Usage: python extract_slack_channel.py --list")
        print("       python extract_slack_channel.py --channel <name-or-id> [--days 30]")
        return

    channel_id = None
    channel_name = None

    if args.channel.startswith("C") and len(args.channel) > 8:
        channel_id = args.channel
        try:
            info = client.conversations_info(channel=channel_id)
            channel_name = info["channel"].get("name", channel_id)
        except SlackApiError:
            channel_name = channel_id
    else:
        channels = list_channels(client)
        clean = args.channel.lstrip("#")
        match = [c for c in channels if c.get("name") == clean]
        if match:
            channel_id = match[0]["id"]
            channel_name = match[0]["name"]
        else:
            print(f"Channel '{args.channel}' not found. Use --list to see available channels.")
            return

    print(f"\nExtracting from #{channel_name} ({channel_id})...")
    messages = extract_channel_messages(
        client, channel_id, days_back=args.days, include_threads=not args.no_threads
    )

    all_user_ids = set()
    for msg in messages:
        all_user_ids.add(msg["user"])
        for reply in msg.get("thread_replies", []):
            all_user_ids.add(reply["user"])

    print("Resolving user names...")
    user_map = resolve_users(client, all_user_ids)

    for msg in messages:
        msg["user_name"] = user_map.get(msg["user"], msg["user"])
        for reply in msg.get("thread_replies", []):
            reply["user_name"] = user_map.get(reply["user"], reply["user"])

    output_path = args.output or f"slack_extract_{channel_name}_{datetime.now().strftime('%Y%m%d')}.json"
    output_data = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "extracted_at": datetime.now().isoformat(),
        "days_back": args.days,
        "total_messages": len(messages),
        "total_thread_replies": sum(len(m.get("thread_replies", [])) for m in messages),
        "users": user_map,
        "messages": messages,
    }
    save_output(output_data, output_path)

    print(f"\nSummary:")
    print(f"  Channel: #{channel_name}")
    print(f"  Period: last {args.days} days")
    print(f"  Messages: {len(messages)}")
    print(f"  Thread replies: {output_data['total_thread_replies']}")
    print(f"  Unique users: {len(user_map)}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
