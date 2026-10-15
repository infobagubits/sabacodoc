from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestNegativeTotalInvoice(AccountTestInvoicingCommon):

    def _negative_invoice(self, move_type="out_invoice"):
        return self.init_invoice(
            move_type,
            partner=self.partner_a,
            invoice_date="2026-01-15",
            amounts=[100.0, -300.0],
        )

    def test_blocked_when_disabled(self):
        self.env.company.allow_negative_total_invoice = False
        invoice = self._negative_invoice()
        with self.assertRaises(UserError):
            invoice.action_post()

    def test_customer_invoice_allowed(self):
        self.env.company.allow_negative_total_invoice = True
        invoice = self._negative_invoice()
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertLess(invoice.amount_total, 0.0)
        # Il valore riletto dal database deve essere quello reale (negativo)
        invoice.invalidate_recordset(["amount_total"])
        self.assertLess(invoice.amount_total, 0.0)

    def test_vendor_bill_allowed(self):
        self.env.company.allow_negative_total_invoice = True
        bill = self._negative_invoice("in_invoice")
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        self.assertLess(bill.amount_total, 0.0)

    def test_credit_note_still_blocked(self):
        self.env.company.allow_negative_total_invoice = True
        refund = self._negative_invoice("out_refund")
        with self.assertRaises(UserError):
            refund.action_post()
