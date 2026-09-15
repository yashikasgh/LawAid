import { PDFDocument, rgb, StandardFonts } from 'pdf-lib'

export type FIRFormData = {
  district: string
  policeStation: string
  year: string
  firNo: string
  firDate: string

  act1: string
  section1: string
  act2: string
  section2: string
  act3: string
  section3: string
  otherActs: string

  occurrenceDay: string
  occurrenceDate: string
  occurrenceTime: string
  informationDate: string
  informationTime: string
  gdEntry: string
  gdTime: string

  informationType: string

  placeDirection: string
  beatNo: string
  placeAddress: string
  outsidePoliceStation: string
  outsideDistrict: string

  complainantName: string
  fatherHusbandName: string
  dob: string
  nationality: string
  passportNo: string
  passportDate: string
  passportPlace: string
  occupation: string
  complainantAddress: string

  accusedDetails: string
  delayReason: string
  propertyDetails: string
  propertyValue: string
  inquestDetails: string
  firContents: string

  actionTaken: string
  officerRank: string
  officerName: string
  officerNo: string

  dispatchDate: string
  dispatchTime: string

  statement?: string
}

const PAGE_HEIGHT = 792

function clean(value?: string) {
  return value?.trim() || ''
}

const TEXT_OFFSET = 8

function pdfY(topY: number) {
  return PAGE_HEIGHT - (topY + TEXT_OFFSET)
}

function drawText(
  page: any,
  font: any,
  text: string | undefined,
  x: number,
  topY: number,
  size = 7
) {
  const value = clean(text)

  if (!value) return

  page.drawText(value, {
    x,
    y: pdfY(topY),
    size,
    font,
    color: rgb(0, 0, 0),
  })
}

function coverLine(
  page: any,
  x: number,
  topY: number,
  width: number,
  height = 12
) {
  page.drawRectangle({
    x,
    y: pdfY(topY) - 2,
    width,
    height,
    color: rgb(1, 1, 1),
  })
}

function drawField(
  page: any,
  font: any,
  text: string | undefined,
  x: number,
  topY: number,
  width: number,
  size = 7
) {
  const value = clean(text)

  if (!value) return

  coverLine(page, x, topY, width)

  drawText(page, font, value, x, topY, size)
}

function drawLines(
  page: any,
  font: any,
  text: string | undefined,
  x: number,
  firstTopY: number,
  width: number,
  lineCount: number,
  size = 7,
  lineGap = 14
) {
  const value = clean(text)

  if (!value) return

  const words = value.split(/\s+/)
  const lines: string[] = []
  let current = ''

  for (const word of words) {
    const test = current ? `${current} ${word}` : word

    const estimatedWidth = test.length * size * 0.52

    if (estimatedWidth <= width) {
      current = test
    } else {
      if (current) {
        lines.push(current)
      }

      current = word
    }

    if (lines.length >= lineCount) {
      break
    }
  }

  if (lines.length < lineCount && current) {
    lines.push(current)
  }

  for (let i = 0; i < Math.min(lines.length, lineCount); i++) {
    const y = firstTopY + i * lineGap

    coverLine(page, x, y, width)

    drawText(
      page,
      font,
      lines[i],
      x,
      y,
      size
    )
  }
}

export async function generateFIRPdf(
  form: FIRFormData
): Promise<Uint8Array> {
  const response = await fetch('/templates/FORM%20FIR.pdf')

  if (!response.ok) {
    throw new Error('Unable to load FIR template.')
  }

  const templateBytes = await response.arrayBuffer()

  const pdfDoc = await PDFDocument.load(templateBytes)

  const font = await pdfDoc.embedFont(
    StandardFonts.Helvetica
  )

  const pages = pdfDoc.getPages()

  if (pages.length < 2) {
    throw new Error(
      'Invalid FIR template. Expected 2 pages.'
    )
  }

  const page1 = pages[0]
  const page2 = pages[1]

  /*
   * =========================================================
   * PAGE 1
   * =========================================================
   */

  // ---------------------------------------------------------
  // 1. FIR Identification
  // ---------------------------------------------------------

  drawField(
    page1,
    font,
    form.district,
    98,
    116,
    64
  )

  drawField(
    page1,
    font,
    form.policeStation,
    211,
    116,
    73,
    6.5
  )

  drawField(
    page1,
    font,
    form.year,
    290,
    116,
    64
  )

  drawField(
    page1,
    font,
    form.firNo,
    414,
    116,
    62
  )

  drawField(
    page1,
    font,
    form.firDate,
    508,
    116,
    47
  )

  // ---------------------------------------------------------
  // 2. Acts and Sections
  // ---------------------------------------------------------

  drawField(
    page1,
    font,
    form.act1,
    126,
    144,
    157,
    6.5
  )

  drawField(
    page1,
    font,
    form.section1,
    341,
    144,
    212,
    6.5
  )

  drawField(
    page1,
    font,
    form.act2,
    126,
    165,
    157,
    6.5
  )

  drawField(
    page1,
    font,
    form.section2,
    341,
    165,
    212,
    6.5
  )

  drawField(
    page1,
    font,
    form.act3,
    126,
    186,
    157,
    6.5
  )

  drawField(
    page1,
    font,
    form.section3,
    341,
    186,
    212,
    6.5
  )

  drawField(
    page1,
    font,
    form.otherActs,
    223,
    207,
    330,
    6.5
  )

  // ---------------------------------------------------------
  // 3. Occurrence of Offence
  // ---------------------------------------------------------

  drawField(
    page1,
    font,
    form.occurrenceDay,
    260,
    240,
    50,
    6.5
  )

  drawField(
    page1,
    font,
    form.occurrenceDate,
    367,
    240,
    87,
    6.5
  )

  drawField(
    page1,
    font,
    form.occurrenceTime,
    491,
    240,
    63,
    6.5
  )

  drawField(
    page1,
    font,
    form.informationDate,
    267,
    268,
    119,
    6.5
  )

  drawField(
    page1,
    font,
    form.informationTime,
    418,
    268,
    138,
    6.5
  )

  drawField(
    page1,
    font,
    form.gdEntry,
    286,
    295,
    96,
    6.5
  )

  drawField(
    page1,
    font,
    form.gdTime,
    414,
    295,
    144,
    6.5
  )

  // ---------------------------------------------------------
  // 4. Type of Information
  // ---------------------------------------------------------

  drawField(
    page1,
    font,
    form.informationType,
    365,
    323,
    190,
    7
  )

  // ---------------------------------------------------------
  // 5. Place of Occurrence
  // ---------------------------------------------------------

  drawField(
    page1,
    font,
    form.placeDirection,
    354,
    351,
    83,
    6.5
  )

  drawField(
    page1,
    font,
    form.beatNo,
    487,
    351,
    66,
    6.5
  )

  drawLines(
    page1,
    font,
    form.placeAddress,
    151,
    378,
    399,
    2,
    6.5,
    14
  )

  drawField(
    page1,
    font,
    form.outsidePoliceStation,
    412,
    406,
    138,
    6.5
  )

  drawField(
    page1,
    font,
    form.outsideDistrict,
    139,
    420,
    132,
    6.5
  )

  // ---------------------------------------------------------
  // 6. Complainant / Information
  // ---------------------------------------------------------

  drawField(
    page1,
    font,
    form.complainantName,
    132,
    475,
    423,
    7
  )

  drawField(
    page1,
    font,
    form.fatherHusbandName,
    235,
    497,
    320,
    7
  )

  drawField(
    page1,
    font,
    form.dob,
    202,
    517,
    180,
    6.5
  )

  drawField(
    page1,
    font,
    form.nationality,
    459,
    517,
    99,
    6.5
  )

  drawField(
    page1,
    font,
    form.passportNo,
    165,
    538,
    90,
    6.5
  )

  drawField(
    page1,
    font,
    form.passportDate,
    327,
    538,
    78,
    6.5
  )

  drawField(
    page1,
    font,
    form.passportPlace,
    478,
    538,
    78,
    6.5
  )

  drawField(
    page1,
    font,
    form.occupation,
    162,
    559,
    396,
    7
  )

  drawField(
    page1,
    font,
    form.complainantAddress,
    146,
    580,
    410,
    7
  )

  // ---------------------------------------------------------
  // 7. Accused Details
  // ---------------------------------------------------------

  drawLines(
    page1,
    font,
    form.accusedDetails,
    72,
    635,
    485,
    3,
    6.5,
    14
  )

  // ---------------------------------------------------------
  // 8. Reason for Delay
  // ---------------------------------------------------------

  const delayReason = clean(form.delayReason)

  if (delayReason) {
    drawLines(
      page1,
      font,
      delayReason,
      375,
      676,
      180,
      1,
      6.5,
      14
    )

    const remainingDelay = delayReason

    if (remainingDelay.length > 40) {
      drawLines(
        page1,
        font,
        remainingDelay,
        72,
        690,
        480,
        2,
        6.5,
        14
      )
    }
  }

  /*
   * =========================================================
   * PAGE 2
   * =========================================================
   */

  // ---------------------------------------------------------
  // 9. Property Details
  // ---------------------------------------------------------

  const propertyDetails = clean(
    form.propertyDetails
  )

  if (propertyDetails) {
    drawLines(
      page1,
      font,
      propertyDetails,
      449,
      718,
      106,
      1,
      6.5,
      14
    )

    drawLines(
      page2,
      font,
      propertyDetails,
      72,
      47,
      485,
      3,
      6.5,
      14
    )
  }

  // ---------------------------------------------------------
  // 10. Total Value
  // ---------------------------------------------------------

  drawField(
    page2,
    font,
    form.propertyValue,
    303,
    102,
    246,
    7
  )

  // ---------------------------------------------------------
  // 11. Inquest Report / U.D. Case
  // ---------------------------------------------------------

  drawLines(
    page2,
    font,
    form.inquestDetails,
    268,
    130,
    282,
    2,
    6.5,
    14
  )

  // ---------------------------------------------------------
  // 12. FIR Contents
  // ---------------------------------------------------------

  drawLines(
    page2,
    font,
    form.firContents,
    72,
    195,
    485,
    10,
    7,
    15
  )

  // ---------------------------------------------------------
  // 13. Action Taken
  // ---------------------------------------------------------

  /*
   * The official template already contains the standard
   * Action Taken text. The editable values that belong in
   * its blank fields are placed below.
   */

  drawField(
    page2,
    font,
    form.officerRank,
    509,
    392,
    49,
    6.5
  )

  drawField(
    page2,
    font,
    form.officerName,
    366,
    489,
    192,
    6.5
  )

  drawField(
    page2,
    font,
    form.officerRank,
    365,
    502,
    112,
    6.5
  )

  drawField(
    page2,
    font,
    form.officerNo,
    483,
    502,
    75,
    6.5
  )

  // ---------------------------------------------------------
  // 15. Date & Time of Despatch to Court
  // ---------------------------------------------------------

  drawField(
    page2,
    font,
    form.dispatchDate,
    250,
    558,
    110,
    6.5
  )

  drawField(
    page2,
    font,
    form.dispatchTime,
    390,
    558,
    100,
    6.5
  )

  return await pdfDoc.save()
}