# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeEvaluation(Document):
	"""Main document for employee contract evaluation using AI."""

	def validate(self):
		"""Validate required files before processing."""
		if self.status == "Processing":
			if not self.eval_file:
				frappe.throw("Vui lòng upload file Đánh giá tái ký")
			if not self.work_report_file:
				frappe.throw("Vui lòng upload file Báo cáo kết quả công việc")
