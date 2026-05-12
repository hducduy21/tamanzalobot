function doGet() {
  // Get the active sheet
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("TỆP KHÁCH");
  
  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({error: "Sheet 'TỆP KHÁCH' không tồn tại"}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  // Get the last row with data
  const lastRow = sheet.getLastRow();

  // Get values from columns K (11) and L (12)
  const data = sheet.getRange(1, 11, lastRow, 2).getValues();

  // Convert data to JSON
  const jsonData = JSON.stringify(data);

  // Return JSON response
  return ContentService.createTextOutput(jsonData)
    .setMimeType(ContentService.MimeType.JSON);
}
function myFunction() {
  const apiUrl = "http://160.191.245.27:8080/api/send-member-v2";
  const adminPhone = "0338739954";
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Data");
  const data = sheet.getDataRange().getValues();

  const ctvMap = {}; // { "Tên CTV": [{ maKH: ..., soNgayHet: ... }, ...] }

  for (let i = 1; i < data.length; i++) {
    const ctv = data[i][3];         // Cột D - Tên CTV
    const maKH = data[i][10];       // Cột K - Mã KH
    let soNgayHet = data[i][8];     // Cột I - Số ngày hết

    if (!ctv || !maKH || soNgayHet === "") continue;

    soNgayHet = Number(soNgayHet);
    if (isNaN(soNgayHet) || soNgayHet < 0) continue;

    if (soNgayHet < 4) {
      if (!ctvMap[ctv]) {
        ctvMap[ctv] = [];
      }
      ctvMap[ctv].push({ maKH, soNgayHet });
    }
  }

  for (let ctv in ctvMap) {
    const danhSach = ctvMap[ctv];

    const theoNgay = {};  // { sốNgày: [maKH1, maKH2, ...] }

    danhSach.forEach(item => {
      const ngay = item.soNgayHet;
      if (!theoNgay[ngay]) {
        theoNgay[ngay] = [];
      }
      theoNgay[ngay].push(item.maKH);
    });

    let message = `CTV ${ctv}\n`;

    // Duyệt từ 3 → 1 ngày
    [3, 2, 1].forEach(ngay => {
      if (theoNgay[ngay]) {
        message += `Các mã còn ${ngay} ngày: ${theoNgay[ngay].join(", ")}\n`;
      }
    });

    // Mã hết hạn (0 ngày)
    if (theoNgay[0]) {
      message += `Các mã đã hết hạn: ${theoNgay[0].join(", ")}\n`;
    }

    const payload = {
      phone: adminPhone,
      msg: message.trim()
    };

    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    UrlFetchApp.fetch(apiUrl, options);
  }
}

var BOT_WEBHOOK_URL = "http://160.191.245.27:5000/warranty";
var SECRET_KEY      = "6b6bbf";

var SHEET_NAME   = "TỆP KHÁCH";
var COL_CTV      = 4;  // D
var COL_WARRANTY = 11; // K
var COL_PASSWORD = 12; // L

// ============================================================

// Nhận request ghi mật khẩu vào cột L, sau đó gửi D+K+L về bot
function doPost(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const ma = e.parameter.ma;         // mã cần tìm trong cột K
  const giaTri = e.parameter.giaTri; // giá trị muốn ghi vào cột L

  const lastRow = sheet.getLastRow();
  let found = false;

  for (let i = 2; i <= lastRow; i++) {
    const valueK = sheet.getRange(i, 11).getValue(); // Cột K là cột 11
    if (valueK == ma) {
      sheet.getRange(i, 12).setValue(giaTri); // Cột L là cột 12
      found = true;

      // Đọc D, K, L rồi gửi về bot
      const ctv      = sheet.getRange(i, COL_CTV).getValue().toString().trim();
      const warranty = sheet.getRange(i, COL_WARRANTY).getValue().toString().trim();
      const password = giaTri.toString().trim();
      _sendToBot(ctv, warranty, password);

      break;
    }
  }

  return ContentService.createTextOutput(
    found ? "Đã cập nhật: " + ma : "Không tìm thấy mã: " + ma
  );
}


// Cần cài installable trigger: Extensions > Apps Script > Triggers > onEditSheet (On edit)
// (Simple trigger không dùng được UrlFetchApp)
function onEditSheet(e) {
  if (!e || !e.range) return;
  var range = e.range;
  var sheet = range.getSheet();

  if (sheet.getName() !== SHEET_NAME) return;
  if (range.getNumRows() !== 1 || range.getNumColumns() !== 1) return; // bỏ qua thay đổi nhiều ô (xóa/chèn hàng...)
  if (range.getColumn() !== COL_PASSWORD) return;  // chỉ cột L
  if (typeof e.value === "undefined") return; // chỉ xử lý nhập trực tiếp 1 ô
  var row = range.getRow();
  if (row < 2) return;  // bỏ qua header

  var ctv      = sheet.getRange(row, COL_CTV).getValue().toString().trim();
  var warranty = sheet.getRange(row, COL_WARRANTY).getValue().toString().trim();
  var password = e.value.toString().trim();

  if (!warranty || !password) return;

  _sendToBot(ctv, warranty, password);
}


function _sendToBot(ctv, warrantyCode, password) {
  var payload = JSON.stringify({
    secret:        SECRET_KEY,
    ctv:           ctv,
    warranty_code: warrantyCode,
    password:      password
  });

  var options = {
    method:             "post",
    contentType:        "application/json",
    payload:            payload,
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(BOT_WEBHOOK_URL, options);
    var code     = response.getResponseCode();
    if (code !== 200) {
      Logger.log("Lỗi HTTP " + code + ": " + response.getContentText());
    }
  } catch (err) {
    Logger.log("Exception: " + err.toString());
  }
}

