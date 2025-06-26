# models/qr_models.py
from importlib.resources._common import _
import pdfkit
from odoo import models, fields, api, _
import qrcode
import base64
from io import BytesIO
from odoo.tools import image_process
from odoo.http import request
import re

from odoo.exceptions import ValidationError, UserError


class QrQr(models.Model):
    _name = 'qr.qr'
    _description = 'QR Code'
    _inherit = "translation.mixin"


    name = fields.Char(string='QR Name',translate=True )
    equipment_id = fields.Many2one('maintenance.equipment', string='Item Name' )
    qr_code = fields.Binary(string='QR Code', attachment=True)
    qr_code_url = fields.Char(string='QR URL',translate=True)
    attachment_ids = fields.One2many('qr.attachments', 'qr_id', string='Attachments')

    @api.model
    def create(self, vals):
        record = super(QrQr, self).create(vals)
        record.generate_qr_code()
        return record

    def write(self, vals):
        result = super(QrQr, self).write(vals)
        if 'equipment_id' in vals or 'name' in vals:
            self.generate_qr_code()
        return result

    def generate_qr_code(self):
        """ Generate QR code for the equipment link """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            qr_url = f"{base_url}/web#id={record.id}&model=qr.qr&view_type=form"
            record.qr_code_url = qr_url

            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(qr_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffered = BytesIO()
            img.save(buffered, format="PNG")
            record.qr_code = base64.b64encode(buffered.getvalue())


class QrAttachments(models.Model):
    _name = 'qr.attachments'
    _description = 'QR Attachments'
    _inherit = "translation.mixin"

    name = fields.Char(string='File Name' ,translate=True)
    qr_id = fields.Many2one('qr.qr', string='QR Code')
    item = fields.Many2one('maintenance.equipment', string='Item')
    item_number = fields.Char(related='item.serial_no', string='Item Number', readonly=True,translate=True)
    document_type = fields.Many2one('qr.document.type',string="Document Type")
    lines_ids=fields.One2many('qr.attachments.line','doc_id',string='Lines')

    @api.onchange('document_type')
    def _onchange_document_type(self):
        """
        When document_type is changed, fetch all previous revisions for this item and document type,
        and populate the lines_ids with those revisions.
        """
        if self.document_type and self.item:
            # Search for existing attachments with same item and document type
            existing_attachments = self.search([
                ('item', '=', self.item.id),
                ('document_type', '=', self.document_type.id),
                ('id', '!=', self._origin.id)  # Exclude current record if it exists
            ])

            # Collect all previous revision lines
            previous_lines = []
            for attachment in existing_attachments:
                for line in attachment.lines_ids:
                    previous_lines.append((0, 0, {
                        'revision_no': line.revision_no,
                        'revision_date': line.revision_date,
                        'pdf_file': line.pdf_file,
                        'pdf_filename': line.pdf_filename,
                    }))

            # Set the lines
            if previous_lines:
                self.lines_ids = previous_lines

    @api.model
    def create(self, vals):
        """
        When creating a new attachment, remove old attachments with the same
        document type and item.
        """
        record = super(QrAttachments, self).create(vals)

        # Find old attachments with same item and document type
        old_attachments = self.search([
            ('item', '=', record.item.id),
            ('document_type', '=', record.document_type.id),
            ('id', '!=', record.id)
        ])

        # Remove old attachments
        if old_attachments:
            old_attachments.unlink()

        return record






class QrDocumentLine(models.Model):
    _name= 'qr.attachments.line'
    _description='Document Line'
    _inherit = "translation.mixin"

    doc_id=fields.Many2one('qr.attachments',string='Document',ondelete="cascade")
    revision_no = fields.Char(string='Revision Number',translate=True)
    revision_date = fields.Date(string='Revision Date')
    pdf_file = fields.Binary(string='PDF File', attachment=True )
    pdf_filename = fields.Char(string='PDF Filename',translate=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    # New fields for manual content
    has_manual_content = fields.Boolean(string='Has Manual Content', default=False,
                                        help="Check this if you want to create manual content instead of uploading a PDF")
    manual_title = fields.Char(string='Manual Title', help="Title for the manual",translate=True)
    manual_content = fields.Html(string='Manual Content', sanitize=True,
                                 help="Create your manual with formatted text, tables, and images",translate=True)

    # Generated PDF from manual content
    generated_pdf = fields.Binary(string='Generated PDF', attachment=True)
    generated_pdf_filename = fields.Char(string='Generated PDF Filename',translate=True)

    _sql_constraints = [
        ('unique_revision_per_document',
         'UNIQUE(doc_id, revision_no)',
         'Revision number must be unique for each document!')
    ]

    @staticmethod
    def convert_images_to_base64(html_content):
        """Convert Odoo's relative image URLs to Base64-embedded images."""
        pattern = r'src=[\'"](/web/content/(\d+))[\'"]'

        def replace_img(match):
            attachment_id = int(match.group(2))
            attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

            if attachment and attachment.datas:
                return f'src="data:image/png;base64,{attachment.datas.decode()}"'  # No need to decode & re-encode

            return match.group(0)  # Return original if not found

        return re.sub(pattern, replace_img, html_content)

    def generate_pdf_from_html(self):
        """Generate a PDF report from QWeb template."""
        self.ensure_one()  # Ensure only one record is processed at a time

        try:
            report_ref = 'iatf.report_qr_manual'  # Ensure this XML ID exists in ir.actions.report
            report = self.env.ref(report_ref)

            # Ensure report_ref is a string, not a list
            if isinstance(report_ref, list):
                report_ref = report_ref[0]

            # Ensure we pass a single record instead of a list
            pdf_content, _ = report._render_qweb_pdf(self)

            # Encode PDF content in base64
            pdf_base64 = base64.b64encode(pdf_content)

            # Return PDF as an attachment
            attachment = self.env['ir.attachment'].create({
                'name': 'QR_Manual_Report.pdf',
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            return attachment

        except Exception as e:
            raise UserError(_("PDF generation failed: %s") % str(e))


    @api.onchange('has_manual_content')
    def _onchange_has_manual_content(self):
        """Reset fields based on the content type selection"""
        if self.has_manual_content:
            self.pdf_file = False
            self.pdf_filename = False
        else:
            self.manual_content = False
            self.manual_title = False
            self.generated_pdf = False
            self.generated_pdf_filename = False





    _sql_constraints = [
        ('unique_revision_per_document',
         'UNIQUE(doc_id, revision_no)',
         'Revision number must be unique for each document!')
    ]








class QrDocumentType(models.Model):
    _name = 'qr.document.type'
    _description = 'QR Document Types'
    _inherit = "translation.mixin"

    qr_id = fields.Many2one('qr.qr', string='QR Code')

    name = fields.Char(string='Document Type Name' ,translate=True)
    description = fields.Char(string='Description',translate=True)


class MaintenanceEquipment(models.Model):
    _inherit = ['maintenance.equipment']

    qr_ids = fields.One2many('qr.qr', 'equipment_id', string='QR Codes')
    attachment_ids = fields.One2many('qr.attachments', 'item', string='Attachments')