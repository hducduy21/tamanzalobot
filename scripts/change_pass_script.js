function soSanhVaCapNhatLienFile() {
    // --- CẤU HÌNH THÔNG TIN ---
    const URL_SHEET_2 = "https://docs.google.com/spreadsheets/d/1RL7nNWJthTwfMDnZCZTbw58DLP1bluxBm3HHLbjNgn0/edit?gid=527647863#gid=527647863"; 
    const NAME_SHEET_1 = "NET";   // Tên sheet ở file hiện tại
    const NAME_SHEET_2 = "TỆP KHÁCH"; // Tên sheet ở file đích
    
    // 1. Kết nối File hiện tại (Sheet 1)
    const ss1 = SpreadsheetApp.getActiveSpreadsheet();
    const s1 = ss1.getSheetByName(NAME_SHEET_1);
    
    // 2. Kết nối File thứ hai (Sheet 2) bằng URL
    let ss2;
    try {
      ss2 = SpreadsheetApp.openByUrl(URL_SHEET_2);
    } catch (e) {
      Logger.log("❌ Không thể mở File thứ 2. Hãy kiểm tra URL và quyền truy cập.");
      return;
    }
    const s2 = ss2.getSheetByName(NAME_SHEET_2);
  
    if (!s1 || !s2) {
      Logger.log("❌ Không tìm thấy tên trang tính (Sheet Name) tương ứng.");
      return;
    }
  
    // 3. Lấy dữ liệu từ Sheet 1 (Nguồn)
    const data1 = s1.getDataRange().getValues();
    const mapData = new Map();
  
    // Gom các cặp: Cột D-E (3-4), N-O (13-14), X-Y (23-24)
    for (let i = 1; i < data1.length; i++) {
      const row = data1[i];
      const pairs = [
        { ma: row[3],  val: row[4]  }, 
        { ma: row[13], val: row[14] }, 
        { ma: row[23], val: row[24] }
      ];
  
      pairs.forEach(p => {
        if (p.ma !== "" && p.ma !== undefined) {
          // Lưu vào Map, trim() để tránh lệch do khoảng trắng
          mapData.set(p.ma.toString().trim(), p.val);
        }
      });
    }
  
    // 4. Lấy dữ liệu từ Sheet 2 (Đích)
    const lastRow2 = s2.getLastRow();
    if (lastRow2 < 2) return;

    // Lấy cột D (CTV), K (mã bảo hành), L (mật khẩu)
    const rangeD = s2.getRange(2, 4,  lastRow2 - 1, 1).getValues();
    const rangeK = s2.getRange(2, 11, lastRow2 - 1, 1).getValues();
    const rangeL = s2.getRange(2, 12, lastRow2 - 1, 1).getValues();

    let count = 0;
    const batchItems = [];
    for (let j = 0; j < rangeK.length; j++) {
      const maSheet2 = rangeK[j][0].toString().trim();

      if (mapData.has(maSheet2)) {
        const newPass = mapData.get(maSheet2);
        const oldPass = rangeL[j][0];

        if (oldPass !== "" && oldPass !== null && newPass !== oldPass) {
          const ctv = rangeD[j][0];
          batchItems.push({ ctv: ctv, warranty_code: maSheet2, password: newPass });
        }

        rangeL[j][0] = newPass;
        count++;
      }
    }

    // 5. Ghi dữ liệu mới vào cột L của Sheet 2
    s2.getRange(2, 12, rangeL.length, 1).setValues(rangeL);

    // 6. Gửi batch 1 lần thay vì gọi từng cái
    if (batchItems.length > 0) {
      _sendBatchToBot(batchItems);
    }

    Logger.log(`✅ Thành công! Đã cập nhật ${count} giá trị, gửi batch ${batchItems.length} mục.`);
  }
var BOT_WEBHOOK_URL       = "http://160.191.245.27:5000/warranty";
var BOT_WEBHOOK_BATCH_URL = "http://160.191.245.27:5000/warranty/batch";
var SECRET_KEY            = "6b6bbf";

function _sendBatchToBot(items) {
    var payload = JSON.stringify({
      secret: SECRET_KEY,
      items:  items
    });

    var options = {
      method:             "post",
      contentType:        "application/json",
      payload:            payload,
      muteHttpExceptions: true
    };

    try {
      var response = UrlFetchApp.fetch(BOT_WEBHOOK_BATCH_URL, options);
      var code     = response.getResponseCode();
      if (code !== 200) {
        Logger.log("Batch lỗi HTTP " + code + ": " + response.getContentText());
      } else {
        Logger.log("Batch gửi OK: " + items.length + " mục.");
      }
    } catch (err) {
      Logger.log("Batch exception: " + err.toString());
    }
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