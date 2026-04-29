// Extract all threads from Slack and categorize them
(() => {
  const threads = [];
  const threadList = document.querySelector('[role="list"]');
  
  if (!threadList) return { error: 'Thread list not found' };
  
  // Get all thread items
  const items = threadList.querySelectorAll('[role="listitem"]');
  
  items.forEach((item, index) => {
    // Skip separator items
    if (item.querySelector('separator')) return;
    
    // Find the main thread link (channel name)
    const channelLink = item.querySelector('a[href*="/archives/"][href*="p"]:not([href*="thread_ts"])');
    if (!channelLink) return;
    
    const url = channelLink.href;
    const channelName = channelLink.textContent.trim();
    
    // Extract timestamp from URL
    const tsMatch = url.match(/p(\d+)/);
    const timestamp = tsMatch ? parseInt(tsMatch[1]) : null;
    
    // Get time text
    const timeLink = item.querySelector('a[href*="at"]');
    const timeText = timeLink ? timeLink.textContent.trim() : '';
    
    // Get message preview
    const messageText = item.textContent;
    
    // Check if unread (look for "New" separator or unread indicators)
    const isUnread = item.previousElementSibling?.querySelector('separator') !== null ||
                     item.textContent.includes('New') ||
                     item.querySelector('[class*="unread"]') !== null;
    
    // Get reply count if available
    const replyText = item.textContent.match(/(\d+)\s*(more\s*)?repl(ies|y)/i);
    const replyCount = replyText ? parseInt(replyText[1]) : 0;
    
    threads.push({
      index: index,
      url: url.split('?')[0], // Clean URL
      channel: channelName,
      time: timeText,
      timestamp: timestamp,
      text: messageText.substring(0, 300),
      isUnread: isUnread,
      replyCount: replyCount
    });
  });
  
  return {
    total: threads.length,
    threads: threads,
    unreadCount: threads.filter(t => t.isUnread).length
  };
})();












