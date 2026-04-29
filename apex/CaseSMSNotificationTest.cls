@isTest
private class CaseSMSNotificationTest {

    @isTest
    static void testSendSMS() {
        Test.setMock(HttpCalloutMock.class, new MockSMSResponse());

        Account acc = new Account(Name = 'Test Account');
        insert acc;

        Case c = new Case(
            Subject = 'Test Case',
            Status = 'New',
            AccountId = acc.Id
        );
        insert c;

        CaseSMSNotification.SMSRequest req = new CaseSMSNotification.SMSRequest();
        req.caseId = c.Id;
        req.customerId = acc.Id;
        req.smsText = 'Test SMS message';

        Test.startTest();
        CaseSMSNotification.sendSMS(new List<CaseSMSNotification.SMSRequest>{ req });
        Test.stopTest();
    }

    private class MockSMSResponse implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"success": true}');
            return res;
        }
    }
}
