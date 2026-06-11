# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""OpenAI client wrapper for HR Contract Evaluation.

Reads API key from Agent Hub Settings DocType (preferred),
falling back to Frappe site_config, then environment variable.
"""

import json
import os

import frappe
from openai import OpenAI


def get_api_key():
	"""Retrieve OpenAI API key with fallback chain.

	Priority:
		1. Agent Hub Settings DocType (password field)
		2. frappe.conf (site_config.json: openai_api_key)
		3. OPENAI_API_KEY environment variable

	Returns:
		The API key string.

	Raises:
		frappe.ValidationError: If key is not found in any source.
	"""
	# 1. Try Agent Hub Settings DocType
	try:
		api_key = frappe.get_doc("Agent Hub Settings").get_password("openai_api_key")
		if api_key:
			return api_key
	except Exception:
		pass

	# 2. Fallback to site_config.json
	api_key = frappe.conf.get("openai_api_key")
	if api_key:
		return api_key

	# 3. Fallback to environment variable
	api_key = os.environ.get("OPENAI_API_KEY")
	if api_key:
		return api_key

	frappe.throw(
		"OpenAI API key chưa được cấu hình. "
		"Cấu hình trong Agent Hub Settings hoặc chạy: bench set-config openai_api_key 'sk-xxx'"
	)


def get_client():
	"""Create and return an OpenAI client instance.

	Returns:
		OpenAI client configured with the resolved API key.
	"""
	return OpenAI(api_key=get_api_key())


def chat_completion_json(system_prompt, user_prompt, model="gpt-4o"):
	"""Call OpenAI chat completion and parse JSON response.

	Uses JSON response format to ensure structured output.

	Args:
		system_prompt: System role instructions.
		user_prompt: User message with the task.
		model: OpenAI model to use (default: gpt-4o).

	Returns:
		Parsed JSON object (dict) from the AI response.

	Raises:
		frappe.ValidationError: If the API call fails or response is invalid.
	"""
	client = get_client()

	try:
		content = ""  # khởi tạo trước để tránh UnboundLocalError trong except block
		response = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			response_format={"type": "json_object"},
			temperature=0.3,
			max_tokens=4096,
		)

		content = response.choices[0].message.content

		return json.loads(content)

	except json.JSONDecodeError as e:
		frappe.log_error(
			title="OpenAI JSON Parse Error",
			message=f"Failed to parse AI response as JSON: {e}\nRaw: {content[:500]}"
		)
		frappe.throw("AI trả về kết quả không hợp lệ. Vui lòng thử lại.")
	except Exception as e:
		error_msg = str(e)
		# Avoid logging the full API key in errors
		if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
			frappe.log_error(
				title="OpenAI Authentication Error",
				message="OpenAI API authentication failed. Check your API key."
			)
			frappe.throw("Lỗi xác thực OpenAI API. Vui lòng kiểm tra API key.")
		else:
			frappe.log_error(
				title="OpenAI API Error",
				message=f"OpenAI API call failed: {error_msg[:500]}"
			)
			frappe.throw(f"Lỗi khi gọi OpenAI API: {error_msg[:200]}")
