import { google } from "googleapis";

const SHEET_NAME = "Sheet1";
const HEADERS = ["Patient Name", "Doctor", "Appointment Date", "Time", "Status", "Booked At"];
const COLUMN_WIDTHS = [160, 150, 130, 90, 110, 180];

const auth = new google.auth.GoogleAuth({
    keyFile: "config/credentials.json",
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
});
const sheets = google.sheets({ version: "v4", auth });

const getSheetId = async (spreadsheetId) => {
    const meta = await sheets.spreadsheets.get({ spreadsheetId });
    const sheet = meta.data.sheets.find((s) => s.properties.title === SHEET_NAME);
    if (!sheet) throw new Error(`Sheet "${SHEET_NAME}" not found`);
    return sheet.properties.sheetId;
};

export const setupSheet = async () => {
    const spreadsheetId = process.env.GOOGLE_SHEET_ID;
    if (!spreadsheetId) return;

    const sheetId = await getSheetId(spreadsheetId);
    const current = await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: `${SHEET_NAME}!A1:F1`,
    });
    const firstCell = current.data.values?.[0]?.[0];

    if (firstCell !== HEADERS[0]) {
        await sheets.spreadsheets.batchUpdate({
            spreadsheetId,
            requestBody: {
                requests: [{
                    insertDimension: {
                        range: { sheetId, dimension: "ROWS", startIndex: 0, endIndex: 1 },
                        inheritFromBefore: false,
                    },
                }],
            },
        });
    }

    await sheets.spreadsheets.values.update({
        spreadsheetId,
        range: `${SHEET_NAME}!A1:F1`,
        valueInputOption: "USER_ENTERED",
        requestBody: { values: [HEADERS] },
    });

    const requests = [
        {
            repeatCell: {
                range: { sheetId, startRowIndex: 0, endRowIndex: 1, startColumnIndex: 0, endColumnIndex: 6 },
                cell: {
                    userEnteredFormat: {
                        backgroundColor: { red: 0.12, green: 0.31, blue: 0.55 },
                        textFormat: {
                            bold: true,
                            foregroundColor: { red: 1, green: 1, blue: 1 },
                            fontSize: 11,
                            fontFamily: "Arial",
                        },
                        horizontalAlignment: "CENTER",
                        verticalAlignment: "MIDDLE",
                    },
                },
                fields: "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
            },
        },
        {
            updateSheetProperties: {
                properties: { sheetId, gridProperties: { frozenRowCount: 1 } },
                fields: "gridProperties.frozenRowCount",
            },
        },
        {
            updateDimensionProperties: {
                range: { sheetId, dimension: "ROWS", startIndex: 0, endIndex: 1 },
                properties: { pixelSize: 40 },
                fields: "pixelSize",
            },
        },
        ...COLUMN_WIDTHS.map((width, i) => ({
            updateDimensionProperties: {
                range: { sheetId, dimension: "COLUMNS", startIndex: i, endIndex: i + 1 },
                properties: { pixelSize: width },
                fields: "pixelSize",
            },
        })),
        {
            addBanding: {
                bandedRange: {
                    range: { sheetId, startRowIndex: 1, endRowIndex: 1000, startColumnIndex: 0, endColumnIndex: 6 },
                    rowProperties: {
                        firstBandColor: { red: 1, green: 1, blue: 1 },
                        secondBandColor: { red: 0.93, green: 0.96, blue: 0.99 },
                    },
                },
            },
        },
    ];

    try {
        await sheets.spreadsheets.batchUpdate({ spreadsheetId, requestBody: { requests } });
    } catch (error) {
        const msg = error.message || "";
        if (!msg.includes("banding") && !msg.includes("alternating background")) throw error;
        await sheets.spreadsheets.batchUpdate({
            spreadsheetId,
            requestBody: { requests: requests.filter((r) => !r.addBanding) },
        });
    }

    await sheets.spreadsheets.batchUpdate({
        spreadsheetId,
        requestBody: {
            requests: [{
                updateSpreadsheetProperties: {
                    properties: { title: "Appointment Bookings" },
                    fields: "title",
                },
            }],
        },
    });
};

export const addToSheet = async (data) => {
    await sheets.spreadsheets.values.append({
        spreadsheetId: process.env.GOOGLE_SHEET_ID,
        range: `${SHEET_NAME}!A:F`,
        valueInputOption: "USER_ENTERED",
        requestBody: {
            values: [[
                data.name,
                data.doctor,
                data.date,
                data.time,
                data.status,
                new Date().toLocaleString(),
            ]],
        },
    });
};
