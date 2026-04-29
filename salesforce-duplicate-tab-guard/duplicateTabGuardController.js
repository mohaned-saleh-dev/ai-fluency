({
    doInit : function(component, event, helper) {
        try {
            var STORAGE_KEY = 'sfdc_tab_guard_heartbeat';
            var HEARTBEAT_INTERVAL = 2000;
            var HEARTBEAT_TIMEOUT = 5000;

            var lastHeartbeat = localStorage.getItem(STORAGE_KEY);
            var now = Date.now();
            var anotherTabIsAlive = lastHeartbeat && (now - parseInt(lastHeartbeat, 10)) < HEARTBEAT_TIMEOUT;

            if (anotherTabIsAlive) {
                try {
                    var navEvent = $A.get("e.force:navigateToURL");
                    navEvent.setParams({"url": "/apex/DuplicateTabWarning"});
                    navEvent.fire();
                } catch(navErr) {
                    try {
                        window.location.href = '/apex/DuplicateTabWarning';
                    } catch(locErr) {}
                }

                window.setTimeout(
                    $A.getCallback(function() {
                        try {
                            window.location.href = '/apex/DuplicateTabWarning';
                        } catch(e) {}
                    }),
                    1500
                );

                return;
            }

            localStorage.setItem(STORAGE_KEY, now.toString());

            window.setInterval(
                $A.getCallback(function() {
                    localStorage.setItem(STORAGE_KEY, Date.now().toString());
                }),
                HEARTBEAT_INTERVAL
            );

            window.addEventListener('beforeunload', function() {
                localStorage.removeItem(STORAGE_KEY);
            });

        } catch (e) {
            console.warn('DuplicateTabGuard error: ' + e.message);
        }
    }
})
