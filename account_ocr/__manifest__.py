{
    "name": "Account OCR",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Launch OCR from vendor bills main attachment",
    "sequence": 20,
    "author": "Anang Aji Rahmawan",
    "website": "https://github.com/0yik",
    "depends": ["account", "document_ocr", "queue_job"],
    "data": [
        "data/queue_job_function_data.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
