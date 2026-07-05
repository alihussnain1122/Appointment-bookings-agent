import express from "express";
import dotenv from "dotenv";
import cors from "cors";
import connectDB from "./config/db.js";
import bookingRoutes from "./routes/bookingRoutes.js";
import { setupSheet } from "./services/googleSheet.js";

dotenv.config();
connectDB();
if (process.env.GOOGLE_SHEET_ID) {
    setupSheet()
        .then(() => console.log("Google Sheet formatted"))
        .catch((err) => console.error("Google Sheet setup failed:", err.message));
}
const app = express();
app.use(cors());
app.use(express.json());
app.use("/api", bookingRoutes);
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});