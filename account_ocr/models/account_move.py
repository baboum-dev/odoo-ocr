from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _validate_main_attachment_ocr(self):
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

    def _run_main_attachment_ocr(self):
        self.ensure_one()
        self._validate_main_attachment_ocr()

        attachment = self.message_main_attachment_id

        document_filename = (
            attachment.name or attachment.datas_fname or _("vendor_bill_document")
        )

        document = (
            self.env["document.ocr"]
            .with_context(target_account_move_id=self.id)
            .create(
                {
                    "name": _("OCR - %s") % (self.ref or self.id),
                    "document_file": attachment.datas,
                    "document_filename": document_filename,
                    "document_type": "vendor_bill",
                    "company_id": self.company_id.id,
                }
            )
        )
        return document.process_document() or self._get_ocr_result_action()

    def _job_run_main_attachment_ocr(self):
        self.ensure_one()
        self._run_main_attachment_ocr()
        return True

    def action_process_main_attachment_ocr(self):
        self.ensure_one()
        return self._run_main_attachment_ocr()

    def action_process_selected_main_attachment_ocr(self):
        queued = 0
        skipped = []

        for move in self:
            try:
                move._validate_main_attachment_ocr()
                job_description = _("OCR Vendor Bill %s") % move.id
                move.with_delay(description=job_description)._job_run_main_attachment_ocr()
                queued += 1
            except UserError as err:
                skipped.append(
                    _(
                        "Invoice %(id)s: %(reason)s",
                        id=move.id,
                        reason=str(err),
                    )
                )

        if not queued and skipped:
            raise UserError(
                _(
                    "No selected invoice could be queued.\n%(details)s",
                    details="\n".join(skipped[:10]),
                )
            )

        message = _("OCR queued for %(count)s invoice(s).", count=queued)
        if skipped:
            message += "\n" + _(
                "%(count)s invoice(s) skipped.",
                count=len(skipped),
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Batch OCR"),
                "message": message,
                "type": "warning" if skipped else "success",
                "sticky": bool(skipped),
            },
        }
