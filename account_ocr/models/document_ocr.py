from odoo import _, fields, models
from odoo.exceptions import UserError


class DocumentOCR(models.Model):
    _inherit = "document.ocr"

    def _get_target_vendor_bill_action(self):
        self.ensure_one()
        target_move_id = self.env.context.get("target_account_move_id")
        if target_move_id:
            target_move = self.env["account.move"].browse(target_move_id).exists()
        else:
            target_move = self.related_record.filtered(lambda record: record._name == "account.move")

        if not target_move:
            return False

        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bill"),
            "res_model": "account.move",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": target_move.id,
            "target": "current",
        }

    def process_document(self):
        result = super().process_document()
        return self._get_target_vendor_bill_action() or result

    def _prepare_vendor_partner(self, parsed_data):
        partner = self.env["res.partner"].search(
            [("name", "ilike", parsed_data.get("vendor_name"))], limit=1
        )
        if partner:
            return partner

        return self.env["res.partner"].create(
            {
                "name": parsed_data.get("vendor_name"),
                "company_type": "company",
                "is_company": True,
            }
        )

    def _prepare_vendor_bill_lines(self, parsed_data):
        lines = []

        for item in parsed_data.get("line_items", []):
            product = self.env["product.product"].search(
                [("name", "ilike", item.get("product"))], limit=1
            )
            if not product:
                product = self.env["product.product"].create(
                    {
                        "name": item.get("product"),
                        "type": "service",
                        "purchase_ok": True,
                    }
                )

            lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": (
                            f"{item.get('product')} {item.get('description')}"
                            if item.get("description")
                            else product.name
                        ),
                        "quantity": item.get("quantity", 1.0),
                        "price_unit": item.get("price", 0.0),
                        "tax_ids": [(5, 0, 0)],
                    },
                )
            )

        if parsed_data.get("total_tax"):
            tax_product = self.env["product.product"].search(
                [("name", "=", "Tax")], limit=1
            ) or self.env["product.product"].create(
                {
                    "name": "Tax",
                    "type": "service",
                    "purchase_ok": True,
                }
            )

            lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": tax_product.id,
                        "name": "Tax",
                        "quantity": 1.0,
                        "price_unit": parsed_data.get("total_tax", 0.0),
                        "tax_ids": [(5, 0, 0)],
                    },
                )
            )

        if parsed_data.get("total_discount"):
            discount_product = self.env["product.product"].search(
                [("name", "=", "Discount")], limit=1
            ) or self.env["product.product"].create(
                {
                    "name": "Discount",
                    "type": "service",
                    "purchase_ok": True,
                }
            )

            lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": discount_product.id,
                        "name": "Discount",
                        "quantity": 1.0,
                        "price_unit": -abs(parsed_data.get("total_discount", 0.0)),
                        "tax_ids": [(5, 0, 0)],
                    },
                )
            )

        return lines

    def _process_data_vendor_bill(self, parsed_data):
        target_move_id = self.env.context.get("target_account_move_id")
        if not target_move_id:
            return super()._process_data_vendor_bill(parsed_data)

        self.ensure_one()
        target_move = self.env["account.move"].browse(target_move_id).exists()
        if not target_move:
            raise UserError(_("Target vendor bill not found."))

        if target_move.move_type != "in_invoice":
            raise UserError(_("OCR target must be a vendor bill."))

        if target_move.state != "draft":
            raise UserError(_("OCR target vendor bill must be in draft state."))

        partner = self._prepare_vendor_partner(parsed_data)
        line_commands = self._prepare_vendor_bill_lines(parsed_data)

        parsed_date = (
            self._parse_date(parsed_data.get("date"))
            or target_move.invoice_date
            or target_move.date
            or fields.Date.context_today(self)
        )
        target_move.write(
            {
                "partner_id": partner.id,
                "invoice_date": parsed_date,
                "date": parsed_date,
                "ref": parsed_data.get("invoice_number"),
                "invoice_line_ids": [(5, 0, 0)] + line_commands,
            }
        )
        self.related_record = target_move
