public class CaseSMSNotification {

    private static final String ENDPOINT = 'https://api-staging.tamara.co/agent/salesforce/send-sms';
    private static final String AUTH_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhY2NvdW50SWQiOiJzYWxlc2ZvcmNlIiwidHlwZSI6InN5c3RlbSIsInNhbHQiOiIiLCJyb2xlcyI6WyJST0xFX1NZU1RFTV9TQUxFU0ZPUkNFIl0sImlhdCI6MTc3NTIxNjE4MiwiaXNzIjoiVGFtYXJhIn0.ae2G2ci-Sngc53WvOPw4w5Lety2iBk859zfzeiFJXr_Li9eJWSo_MYbCS57fSmc0aKtkejHNcPB1RA9nw02MnXWFWdYjOg-k7SUoof3wmnt-FUDyBJb-Cm2Q5xBiP-D_3NM_IVUX2KjnRdW8vaNjflHNwfIRP2L-4vrRw64GlgYCN-q4ne-lqOjFKc7reruBk0NSdiRNOEg8WeYRLisUWG9ZA0kq-fpkEMAefRHzn5KyMck7ZtdxKxczcRdCHGtIumHbYq5-2-rswAK9PmnWe57kCbRcoznxKdnhax9p_xO80_DczxB_aHhx-5oLY9whHv5pcuMITydJhf6P7L4k-w';

    @InvocableMethod(label='Send Case SMS Notification' description='Sends SMS notification via Tamara backend API' category='Case')
    public static void sendSMS(List<SMSRequest> requests) {
        for (SMSRequest req : requests) {
            sendSMSAsync(req.caseId, req.customerId, req.smsText);
        }
    }

    @future(callout=true)
    private static void sendSMSAsync(String caseId, String customerId, String smsText) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(ENDPOINT);
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('Authorization', 'Bearer ' + AUTH_TOKEN);

        String body = JSON.serialize(new Map<String, String>{
            'case_id' => caseId,
            'customer_id' => customerId,
            'text' => smsText
        });
        req.setBody(body);

        try {
            Http http = new Http();
            HttpResponse res = http.send(req);
            if (res.getStatusCode() >= 400) {
                System.debug(LoggingLevel.ERROR, 'CaseSMSNotification failed: ' + res.getStatusCode() + ' ' + res.getBody());
            }
        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR, 'CaseSMSNotification exception: ' + e.getMessage());
        }
    }

    public class SMSRequest {
        @InvocableVariable(required=true label='Case ID' description='Salesforce Case record ID')
        public String caseId;

        @InvocableVariable(required=true label='Customer ID' description='Account ID from the Case')
        public String customerId;

        @InvocableVariable(required=true label='SMS Text' description='The SMS message body')
        public String smsText;
    }
}
