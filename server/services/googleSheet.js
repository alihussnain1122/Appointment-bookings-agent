import { google } from "googleapis";
const auth = new google.auth.GoogleAuth(
    {
        keyFile: "config/credentials.json",
        scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });
const sheets = google.sheets(
    { version: "v4", auth });
export const addToSheet = async (data) => {
    await sheets.spreadsheets.values.append(
        {
            spreadsheetId: process.env.GOOGLE_SHEET_ID,
            range: "Appointments!A:F",
            valueInputOption: "USER_ENTERED",
            requestBody: {
                values: [[
                    data.name,
                    data.doctor,
                    data.date,
                    data.time,
                    data.status,
                    new Date().toLocaleString()
                ]]
            },
        });
};