import pdfParse from 'pdf-parse';

export interface PdfParseResult {
  text: string;
  pages: number;
  isOcrNeeded: boolean;
}

export async function parsePdf(buffer: Buffer): Promise<PdfParseResult> {
  try {
    const data = await pdfParse(buffer);

    const text = data.text.trim();
    const isOcrNeeded = text.length < 50; // テキストが少なすぎる場合はOCRが必要

    return {
      text,
      pages: data.numpages,
      isOcrNeeded,
    };
  } catch (err) {
    console.error('PDFパースエラー:', err);
    return {
      text: '',
      pages: 0,
      isOcrNeeded: true,
    };
  }
}
