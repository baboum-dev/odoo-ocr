from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_ocr_result_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bill"),
            "res_model": "account.move",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
            "target": "current",
        }

    def action_process_main_attachment_ocr(self):
        self.ensure_one()

        if self.move_type != "in_invoice":
            raise UserError(_("OCR is only available for vendor bills."))

        if self.state != "draft":
            raise UserError(_("OCR can only be run on draft vendor bills."))

        attachment = self.message_main_attachment_id
        if not attachment:
            raise UserError(_("Please set a main attachment before running OCR."))

        if attachment.type != "binary" or not attachment.datas:
            raise UserError(_("The main attachment must be a binary file."))

        document_filename = (
            attachment.name or attachment.datas_fname or _("vendor_bill_document")
        )

        document = (
            self.env["document.ocr"]
            .with_context(target_account_move_id=self.id)
            .create(
                {
                    "name": _("OCR - %s") % (self.name or self.ref or self.id),
                    "document_file": attachment.datas,
                    "document_filename": document_filename,
                    "document_type": "vendor_bill",
                    "company_id": self.company_id.id,
                }
            )
        )
        return document.process_document() or self._get_ocr_result_action()
