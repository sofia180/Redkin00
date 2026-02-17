const SHEET_NAME = "Leads";

function doPost(e) {
  const body = e && e.postData && e.postData.contents ? e.postData.contents : "{}";
  const data = JSON.parse(body);

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

  const headers = [
    "created_at",
    "niche",
    "name",
    "phone",
    "email",
    "budget",
    "region",
    "timeframe",
    "contacted_before",
    "status",
  ];

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
  }

  const row = headers.map((key) => (data[key] !== undefined ? data[key] : ""));
  sheet.appendRow(row);

  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
