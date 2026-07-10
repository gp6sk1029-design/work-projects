export interface PdfPageInfo {
  index: number;
  pageNumber: number;
  filename: string;
  phash: string;
  width: number;
  height: number;
  headerText: string;
}

export interface PixelDiffRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PixelDiffInfo {
  rects: PixelDiffRect[];
  totalArea: number;
  changedRatio: number;
  diffImageA: string;
  diffImageB: string;
}

export interface PdfMatch {
  aIndex: number | null;
  bIndex: number | null;
  hamming: number;
  status: 'exact' | 'similar' | 'a_only' | 'b_only';
  pixelDiff?: PixelDiffInfo | null;
}

export interface PdfDiffResponse {
  jobId: string;
  projectAName: string;
  projectBName: string;
  imageBaseUrl: string;
  pagesA: PdfPageInfo[];
  pagesB: PdfPageInfo[];
  matches: PdfMatch[];
  summary: {
    pagesA: number;
    pagesB: number;
    exactMatches: number;
    similarMatches: number;
    onlyInA: number;
    onlyInB: number;
  };
}
