import { PDFDocument, rgb, StandardFonts } from 'pdf-lib'
import { policeAPI } from '@/lib/api'

export type ActSectionEntry = {
  act: string
  section: string
  source?: 'ai' | 'manual'
}

export type BnsSuggestion = {
  id: string
  section: string
  title: string
  act: string
  why_it_may_apply: string
  supporting_facts: string[]
  uncertainty: string[]
  punishment: string
  grounding_source: string
  status: string
  applicability: string
  accepted?: boolean
  removed?: boolean
}

export type FIRFormData = {
  district: string
  policeStation: string
  year: string
  firNo: string
  firDate: string

  actEntries?: ActSectionEntry[]
  legalSuggestions?: BnsSuggestion[]
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

/**
 * Clean text to ensure WinAnsi encoding compatibility in pdf-lib.
 * Replaces Rupee symbol '₹' with 'Rs. ' and removes characters outside ASCII/WinAnsi.
 */
function cleanText(value?: string): string {
  if (!value) return ''
  return value
    .replace(/₹/g, 'Rs. ')
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u2013\u2014]/g, '-')
    .replace(/[^\x00-\x7F]/g, '')
    .trim()
}

/**
 * Splits text into wrapped lines based on font width measurements.
 */
function wrapText(text: string, font: any, fontSize: number, maxWidth: number): string[] {
  const cleaned = cleanText(text)
  if (!cleaned) return []

  const paragraphs = cleaned.split('\n')
  const lines: string[] = []

  for (const para of paragraphs) {
    if (!para.trim()) {
      lines.push('')
      continue
    }
    const words = para.trim().split(/\s+/)
    let currentLine = ''

    for (const word of words) {
      const testLine = currentLine ? `${currentLine} ${word}` : word
      const width = font.widthOfTextAtSize(testLine, fontSize)
      if (width <= maxWidth) {
        currentLine = testLine
      } else {
        if (currentLine) lines.push(currentLine)
        currentLine = word
      }
    }
    if (currentLine) {
      lines.push(currentLine)
    }
  }

  return lines
}

export async function generateFIRPdf(form: FIRFormData): Promise<Uint8Array> {
  try {
    const res = await policeAPI.renderFirPdf(form)
    if (res?.data?.pdf_base64) {
      const base64 = res.data.pdf_base64
      const binaryString = typeof window !== 'undefined' ? window.atob(base64) : Buffer.from(base64, 'base64').toString('binary')
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      return bytes
    }
  } catch (err) {
    console.warn('Failed to render PDF using template API, falling back to local generator:', err)
  }

  const pdfDoc = await PDFDocument.create()
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica)
  const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold)
  const fontItalic = await pdfDoc.embedFont(StandardFonts.HelveticaOblique)

  // Standard A4 dimensions
  const PAGE_WIDTH = 595.28
  const PAGE_HEIGHT = 841.89
  const MARGIN_LEFT = 40
  const MARGIN_RIGHT = 40
  const MARGIN_TOP = 40
  const MARGIN_BOTTOM = 45
  const CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

  let currentPage = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT])
  let yPos = PAGE_HEIGHT - MARGIN_TOP

  function checkPageSpace(neededHeight: number) {
    if (yPos - neededHeight < MARGIN_BOTTOM) {
      currentPage = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT])
      yPos = PAGE_HEIGHT - MARGIN_TOP

      // Continuation Header
      currentPage.drawText('FORM F.I.R. (IF1) - CONTINUED', {
        x: MARGIN_LEFT,
        y: yPos - 12,
        size: 9,
        font: fontBold,
        color: rgb(0.07, 0.20, 0.36),
      })

      const firInfo = `FIR No: ${cleanText(form.firNo) || 'Draft'} | P.S.: ${cleanText(form.policeStation) || 'N/A'} | Date: ${cleanText(form.firDate) || 'N/A'}`
      const infoWidth = font.widthOfTextAtSize(firInfo, 8)
      currentPage.drawText(firInfo, {
        x: PAGE_WIDTH - MARGIN_RIGHT - infoWidth,
        y: yPos - 12,
        size: 8,
        font: font,
        color: rgb(0.3, 0.3, 0.3),
      })

      yPos -= 20
      currentPage.drawLine({
        start: { x: MARGIN_LEFT, y: yPos },
        end: { x: PAGE_WIDTH - MARGIN_RIGHT, y: yPos },
        thickness: 0.8,
        color: rgb(0.7, 0.7, 0.7),
      })
      yPos -= 15
    }
  }

  function drawSectionHeader(title: string) {
    checkPageSpace(26)
    currentPage.drawRectangle({
      x: MARGIN_LEFT,
      y: yPos - 18,
      width: CONTENT_WIDTH,
      height: 18,
      color: rgb(0.93, 0.95, 0.98),
      borderColor: rgb(0.7, 0.78, 0.88),
      borderWidth: 0.5,
    })
    currentPage.drawText(title.toUpperCase(), {
      x: MARGIN_LEFT + 8,
      y: yPos - 13,
      size: 9.5,
      font: fontBold,
      color: rgb(0.07, 0.20, 0.36),
    })
    yPos -= 24
  }

  function drawFieldRow(fields: { label: string; value: string; flex?: number }[]) {
    const totalFlex = fields.reduce((sum, f) => sum + (f.flex || 1), 0)
    let currentX = MARGIN_LEFT

    let maxLines = 1
    const fieldLinesList: { lines: string[]; width: number; x: number; label: string }[] = []

    fields.forEach((f) => {
      const fieldWidth = (CONTENT_WIDTH * (f.flex || 1)) / totalFlex
      const labelText = f.label ? `${f.label}: ` : ''
      const valText = cleanText(f.value) || 'N/A'
      const fullText = labelText ? `${labelText}${valText}` : valText

      const wrapped = wrapText(fullText, font, 8.5, fieldWidth - 10)
      if (wrapped.length > maxLines) maxLines = wrapped.length

      fieldLinesList.push({
        lines: wrapped,
        width: fieldWidth,
        x: currentX,
        label: f.label,
      })
      currentX += fieldWidth
    })

    const rowHeight = Math.max(20, maxLines * 12 + 6)
    checkPageSpace(rowHeight + 4)

    fieldLinesList.forEach((item) => {
      currentPage.drawRectangle({
        x: item.x,
        y: yPos - rowHeight,
        width: item.width,
        height: rowHeight,
        borderColor: rgb(0.82, 0.85, 0.88),
        borderWidth: 0.5,
      })

      let textY = yPos - 14
      item.lines.forEach((line) => {
        if (item.label && line.startsWith(`${item.label}: `)) {
          const labelPart = `${item.label}: `
          const valPart = line.substring(labelPart.length)
          currentPage.drawText(labelPart, {
            x: item.x + 6,
            y: textY,
            size: 8.5,
            font: fontBold,
            color: rgb(0.15, 0.22, 0.33),
          })
          const labelWidth = fontBold.widthOfTextAtSize(labelPart, 8.5)
          currentPage.drawText(valPart, {
            x: item.x + 6 + labelWidth,
            y: textY,
            size: 8.5,
            font: font,
            color: rgb(0.1, 0.1, 0.1),
          })
        } else {
          currentPage.drawText(line, {
            x: item.x + 6,
            y: textY,
            size: 8.5,
            font: font,
            color: rgb(0.1, 0.1, 0.1),
          })
        }
        textY -= 12
      })
    })

    yPos -= rowHeight + 3
  }

  function drawTextBlock(title: string, text: string) {
    drawSectionHeader(title)
    const valText = cleanText(text) || 'Nil / Not provided'
    const wrappedLines = wrapText(valText, font, 9, CONTENT_WIDTH - 16)

    checkPageSpace(30)

    wrappedLines.forEach((line) => {
      checkPageSpace(15)
      currentPage.drawText(line, {
        x: MARGIN_LEFT + 8,
        y: yPos - 10,
        size: 9,
        font: font,
        color: rgb(0.1, 0.1, 0.1),
      })
      yPos -= 13
    })

    yPos -= 10
  }

  // ---------------------------------------------------------
  // DOCUMENT HEADER
  // ---------------------------------------------------------
  const title1 = 'FORM F.I.R. (IF1)'
  const w1 = fontBold.widthOfTextAtSize(title1, 14)
  currentPage.drawText(title1, {
    x: (PAGE_WIDTH - w1) / 2,
    y: yPos - 14,
    size: 14,
    font: fontBold,
    color: rgb(0.07, 0.20, 0.36),
  })
  yPos -= 18

  const title2 = 'FIRST INFORMATION REPORT'
  const w2 = fontBold.widthOfTextAtSize(title2, 11)
  currentPage.drawText(title2, {
    x: (PAGE_WIDTH - w2) / 2,
    y: yPos - 11,
    size: 11,
    font: fontBold,
    color: rgb(0.15, 0.22, 0.33),
  })
  yPos -= 14

  const title3 = '(Under Section 173 Cr.P.C. / Section 175 BNSS)'
  const w3 = fontItalic.widthOfTextAtSize(title3, 8.5)
  currentPage.drawText(title3, {
    x: (PAGE_WIDTH - w3) / 2,
    y: yPos - 9,
    size: 8.5,
    font: fontItalic,
    color: rgb(0.4, 0.4, 0.4),
  })
  yPos -= 18

  currentPage.drawLine({
    start: { x: MARGIN_LEFT, y: yPos },
    end: { x: PAGE_WIDTH - MARGIN_RIGHT, y: yPos },
    thickness: 1,
    color: rgb(0.07, 0.20, 0.36),
  })
  yPos -= 16

  // ---------------------------------------------------------
  // 1. FIR IDENTIFICATION
  // ---------------------------------------------------------
  drawFieldRow([
    { label: 'District', value: form.district, flex: 1.2 },
    { label: 'Police Station', value: form.policeStation, flex: 1.4 },
    { label: 'Year', value: form.year, flex: 0.8 },
    { label: 'FIR No', value: form.firNo, flex: 1.1 },
    { label: 'Date', value: form.firDate, flex: 1.1 },
  ])

  // ---------------------------------------------------------
  // 2. ACTS & SECTIONS (OFFICER-ACCEPTED PROVISIONS ONLY)
  // ---------------------------------------------------------
  drawSectionHeader('2. Acts and Sections (Officer-Reviewed & Accepted)')

  function getAcceptedProvisions(): string[] {
    const list: string[] = []

    // 1. If legalSuggestions available, include ONLY accepted (and not removed) items
    if (form.legalSuggestions && form.legalSuggestions.length > 0) {
      form.legalSuggestions.forEach((sug) => {
        if (sug.accepted && !sug.removed) {
          const actName = cleanText(sug.act) || 'Bharatiya Nyaya Sanhita, 2023'
          const secTitle = sug.title ? `Section ${sug.section} (${sug.title})` : `Section ${sug.section}`
          list.push(`${actName} - ${secTitle}`)
        }
      })
    }

    // 2. If actEntries exists and list is empty, use entries
    if (list.length === 0 && form.actEntries && form.actEntries.length > 0) {
      form.actEntries.forEach((entry) => {
        if (entry.section && entry.section.trim()) {
          const actName = cleanText(entry.act) || 'Bharatiya Nyaya Sanhita, 2023'
          const secText = cleanText(entry.section)
          list.push(`${actName} - ${secText}`)
        }
      })
    }

    // 3. Fallback to act1/sec1 etc.
    if (list.length === 0) {
      if (form.act1 && form.section1) list.push(`${cleanText(form.act1)} - Section ${cleanText(form.section1)}`)
      if (form.act2 && form.section2) list.push(`${cleanText(form.act2)} - Section ${cleanText(form.section2)}`)
      if (form.act3 && form.section3) list.push(`${cleanText(form.act3)} - Section ${cleanText(form.section3)}`)
      if (form.otherActs) list.push(cleanText(form.otherActs))
    }

    return list
  }

  const acceptedProvisions = getAcceptedProvisions()
  if (acceptedProvisions.length === 0) {
    drawFieldRow([{ label: 'Provisions', value: 'Nil / As specified in narrative' }])
  } else {
    acceptedProvisions.forEach((prov, idx) => {
      drawFieldRow([{ label: `Provision ${idx + 1}`, value: prov }])
    })
  }

  // ---------------------------------------------------------
  // 3. OCCURRENCE OF OFFENCE
  // ---------------------------------------------------------
  drawSectionHeader('3. Occurrence of Offence')
  drawFieldRow([
    { label: 'Day', value: form.occurrenceDay, flex: 1 },
    { label: 'Date', value: form.occurrenceDate, flex: 1.5 },
    { label: 'Time', value: form.occurrenceTime, flex: 1.2 },
  ])
  drawFieldRow([
    { label: 'Information Received Date', value: form.informationDate, flex: 1.5 },
    { label: 'Time', value: form.informationTime, flex: 1 },
  ])
  drawFieldRow([
    { label: 'General Diary Reference Entry No', value: form.gdEntry, flex: 1.5 },
    { label: 'GD Time', value: form.gdTime, flex: 1 },
  ])

  // ---------------------------------------------------------
  // 4. TYPE OF INFORMATION
  // ---------------------------------------------------------
  drawSectionHeader('4. Type of Information')
  drawFieldRow([{ label: 'Type', value: form.informationType || 'Written' }])

  // ---------------------------------------------------------
  // 5. PLACE OF OCCURRENCE
  // ---------------------------------------------------------
  drawSectionHeader('5. Place of Occurrence')
  drawFieldRow([
    { label: 'Direction & Distance from P.S.', value: form.placeDirection, flex: 1.5 },
    { label: 'Beat No', value: form.beatNo, flex: 1 },
  ])
  drawFieldRow([{ label: 'Address', value: form.placeAddress }])
  if (cleanText(form.outsidePoliceStation) || cleanText(form.outsideDistrict)) {
    drawFieldRow([
      { label: 'Outside P.S. Limits', value: form.outsidePoliceStation, flex: 1 },
      { label: 'Outside District', value: form.outsideDistrict, flex: 1 },
    ])
  }

  // ---------------------------------------------------------
  // 6. COMPLAINANT / INFORMANT DETAILS
  // ---------------------------------------------------------
  drawSectionHeader('6. Complainant / Informant Details')
  drawFieldRow([{ label: 'Name', value: form.complainantName }])
  drawFieldRow([
    { label: "Father's / Husband's Name", value: form.fatherHusbandName, flex: 1.5 },
    { label: 'Date of Birth / Age', value: form.dob, flex: 1 },
    { label: 'Nationality', value: form.nationality || 'Indian', flex: 1 },
  ])
  if (cleanText(form.passportNo)) {
    drawFieldRow([
      { label: 'Passport No', value: form.passportNo, flex: 1 },
      { label: 'Date of Issue', value: form.passportDate, flex: 1 },
      { label: 'Place of Issue', value: form.passportPlace, flex: 1 },
    ])
  }
  drawFieldRow([
    { label: 'Occupation', value: form.occupation, flex: 1 },
    { label: 'Address', value: form.complainantAddress, flex: 2 },
  ])

  // ---------------------------------------------------------
  // 7. ACCUSED DETAILS
  // ---------------------------------------------------------
  drawTextBlock('7. Details of Known / Suspected / Unknown Accused', form.accusedDetails)

  // ---------------------------------------------------------
  // 8. REASON FOR DELAY IN REPORTING
  // ---------------------------------------------------------
  drawTextBlock('8. Reasons for Delay in Reporting by Complainant / Police', form.delayReason)

  // ---------------------------------------------------------
  // 9. PROPERTY DETAILS & TOTAL VALUE
  // ---------------------------------------------------------
  drawSectionHeader('9. Particulars of Properties Stolen / Involved & Total Value')
  drawFieldRow([
    { label: 'Property Details', value: form.propertyDetails, flex: 2 },
    { label: 'Total Value', value: form.propertyValue, flex: 1 },
  ])

  // ---------------------------------------------------------
  // 10. INQUEST REPORT / U.D. CASE NO.
  // ---------------------------------------------------------
  drawSectionHeader('10. Inquest Report / U.D. Case No.')
  drawFieldRow([{ label: 'Details', value: form.inquestDetails || 'N/A' }])

  // ---------------------------------------------------------
  // 11. FIRST INFORMATION REPORT CONTENTS (NARRATIVE)
  // ---------------------------------------------------------
  const narrative = form.firContents || form.statement || ''
  drawTextBlock('11. First Information Report Contents (Statement of Incident)', narrative)

  // ---------------------------------------------------------
  // 12. ACTION TAKEN & OFFICER DETAILS
  // ---------------------------------------------------------
  drawSectionHeader('12. Action Taken & Investigating Officer Details')
  drawFieldRow([{ label: 'Action Taken', value: form.actionTaken || 'Registered the case and took up investigation' }])
  drawFieldRow([
    { label: 'Investigating Officer Name', value: form.officerName, flex: 1.5 },
    { label: 'Rank', value: form.officerRank, flex: 1 },
    { label: 'No', value: form.officerNo, flex: 1 },
  ])
  drawFieldRow([
    { label: 'Date & Time of Despatch to Court', value: `${cleanText(form.dispatchDate)} ${cleanText(form.dispatchTime)}`.trim() || 'N/A' }
  ])

  // ---------------------------------------------------------
  // SIGNATURE BLOCK
  // ---------------------------------------------------------
  checkPageSpace(75)
  yPos -= 10

  currentPage.drawText('Signature / Thumb Impression of Complainant', {
    x: MARGIN_LEFT,
    y: yPos - 45,
    size: 8.5,
    font: fontBold,
    color: rgb(0.2, 0.2, 0.2),
  })

  const sigRight = 'Signature of Officer in Charge, Police Station'
  const sigRightWidth = fontBold.widthOfTextAtSize(sigRight, 8.5)
  currentPage.drawText(sigRight, {
    x: PAGE_WIDTH - MARGIN_RIGHT - sigRightWidth,
    y: yPos - 45,
    size: 8.5,
    font: fontBold,
    color: rgb(0.2, 0.2, 0.2),
  })

  // ---------------------------------------------------------
  // PAGE NUMBERS IN FOOTER
  // ---------------------------------------------------------
  const pages = pdfDoc.getPages()
  const totalPages = pages.length

  pages.forEach((p, idx) => {
    const pageNumText = `Page ${idx + 1} of ${totalPages}`
    const textWidth = font.widthOfTextAtSize(pageNumText, 8)
    p.drawText(pageNumText, {
      x: (PAGE_WIDTH - textWidth) / 2,
      y: 20,
      size: 8,
      font: font,
      color: rgb(0.4, 0.4, 0.4),
    })
  })

  return await pdfDoc.save()
}