'use client'

import Link from 'next/link'
import { useState, useRef, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import { policeAPI, firDraftsAPI } from '@/lib/api'
import { ActSectionEntry } from '@/lib/pdf/fir-generator'

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

type FormData = {
  district: string
  policeStation: string
  year: string
  firNo: string
  firDate: string

  actEntries: ActSectionEntry[]
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
}

const initialForm: FormData = {
  district: '',
  policeStation: '',
  year: new Date().getFullYear().toString(),
  firNo: 'Draft',
  firDate: new Date().toLocaleDateString('en-GB'),

  actEntries: [
    {
      act: 'Bharatiya Nyaya Sanhita, 2023',
      section: '',
      source: 'manual',
    },
  ],
  act1: 'Bharatiya Nyaya Sanhita, 2023',
  section1: '',
  act2: '',
  section2: '',
  act3: '',
  section3: '',
  otherActs: '',

  occurrenceDay: '',
  occurrenceDate: '',
  occurrenceTime: '',
  informationDate: '',
  informationTime: '',
  gdEntry: '',
  gdTime: '',

  informationType: 'Written',

  placeDirection: '',
  beatNo: '',
  placeAddress: '',
  outsidePoliceStation: '',
  outsideDistrict: '',

  complainantName: '',
  fatherHusbandName: '',
  dob: '',
  nationality: 'Indian',
  passportNo: '',
  passportDate: '',
  passportPlace: '',
  occupation: '',
  complainantAddress: '',

  accusedDetails: '',
  delayReason: '',
  propertyDetails: '',
  propertyValue: '',
  inquestDetails: '',
  firContents: '',

  actionTaken: 'Registered the case and took up the investigation',
  officerRank: '',
  officerName: '',
  officerNo: '',

  dispatchDate: '',
  dispatchTime: '',
}

const SAMPLE_INCIDENTS = [
  {
    title: 'Mobile Snatching in Market',
    text: 'On 14 September 2026 at approximately 8 PM, while the complainant was returning home near the central market, an unknown male suddenly grabbed her mobile phone (iPhone 14 worth ₹65,000) from her hand and fled into the crowd.',
  },
  {
    title: 'Cyber Fraud / Online Cheating',
    text: 'On 12 September 2026, complainant received a fraudulent phone call claiming to be from his bank. The caller induced him to transfer ₹45,000 via UPI under pretext of updating KYC details.',
  },
  {
    title: 'House Theft & Burglary',
    text: 'Between 10 PM on 11 September 2026 and 6 AM on 12 September 2026, unknown persons broke open the main lock of complainant house at 42 Park Street and stole gold ornaments valued at ₹1,20,000 and ₹15,000 cash.',
  },
]

function mapFirDataToFormData(firData: any, sanitizedIncident: string, existingForm?: FormData): FormData {
  const occ = firData?.occurrence || {}
  const place = firData?.place_of_occurrence || {}
  const comp = firData?.complainant || {}
  const officer = firData?.officer || {}
  const info = firData?.information_received || {}
  const gd = firData?.general_diary || {}
  const dispatch = firData?.dispatch_to_court || {}

  const sanitizeVal = (val?: any): string => {
    if (val === null || val === undefined) return ''
    const str = String(val).trim()
    const lower = str.toLowerCase()
    if (
      lower === 'not provided' ||
      lower === 'n/a' ||
      lower === 'unknown' ||
      lower === 'none' ||
      lower === 'null' ||
      lower === 'to be dispatched'
    ) {
      return ''
    }
    return str
  }

  const getFirstVal = (...vals: any[]): string => {
    for (const v of vals) {
      const s = sanitizeVal(v)
      if (s) return s
    }
    return ''
  }

  const incidentText = sanitizedIncident || ''

  // 1. Identification
  const district = getFirstVal(firData?.district, existingForm?.district)
  const policeStation = getFirstVal(firData?.police_station, firData?.policeStation, existingForm?.policeStation)
  const year = getFirstVal(firData?.year, existingForm?.year) || new Date().getFullYear().toString()
  const firNo = getFirstVal(firData?.fir_number, firData?.firNo, existingForm?.firNo) || 'Draft'
  const firDate = getFirstVal(firData?.fir_date, firData?.firDate, existingForm?.firDate) || new Date().toLocaleDateString('en-GB')

  // 2. Occurrence
  let occurrenceDate = getFirstVal(
    occ.date,
    occ.date_from,
    firData?.occurrence_date,
    firData?.occurrenceDate,
    firData?.date,
    existingForm?.occurrenceDate
  )
  let occurrenceTime = getFirstVal(
    occ.time,
    occ.time_from,
    firData?.occurrence_time,
    firData?.occurrenceTime,
    firData?.time,
    existingForm?.occurrenceTime
  )
  let occurrenceDay = getFirstVal(
    occ.day,
    firData?.occurrence_day,
    firData?.occurrenceDay,
    firData?.day,
    existingForm?.occurrenceDay
  )

  if (!occurrenceDate && incidentText) {
    const mDate = incidentText.match(/\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b/i)
    if (mDate) {
      occurrenceDate = mDate[0]
    } else {
      const mSlash = incidentText.match(/\b(\d{1,2}\/\d{1,2}\/\d{2,4})\b/)
      if (mSlash) occurrenceDate = mSlash[0]
    }
  }

  if (!occurrenceTime && incidentText) {
    const mTime = incidentText.match(/\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b/i)
    if (mTime) occurrenceTime = mTime[0]
  }

  // 3. Information type & diary
  const informationType = getFirstVal(firData?.type_of_information, firData?.informationType, existingForm?.informationType) || 'Written'
  const informationDate = getFirstVal(info.date, firData?.informationDate, existingForm?.informationDate)
  const informationTime = getFirstVal(info.time, firData?.informationTime, existingForm?.informationTime)
  const gdEntry = getFirstVal(gd.entry_numbers, firData?.gdEntry, existingForm?.gdEntry)
  const gdTime = getFirstVal(gd.time, firData?.gdTime, existingForm?.gdTime)

  // 4. Place of occurrence
  let placeAddress = getFirstVal(
    place.address,
    firData?.place_address,
    firData?.placeAddress,
    firData?.location,
    firData?.address,
    existingForm?.placeAddress
  )
  const placeDirection = getFirstVal(place.direction_distance_from_ps, firData?.placeDirection, existingForm?.placeDirection)
  const beatNo = getFirstVal(place.beat_no, firData?.beatNo, existingForm?.beatNo)
  const outsidePoliceStation = getFirstVal(place.outside_police_station, firData?.outsidePoliceStation, existingForm?.outsidePoliceStation)
  const outsideDistrict = getFirstVal(place.district, firData?.outsideDistrict, existingForm?.outsideDistrict)

  if (!placeAddress && incidentText) {
    const mLoc = incidentText.match(/\b(?:near|at|around|in)\s+(?:the\s+)?([a-zA-Z0-9\s,-]+?(?:market|road|street|station|bus stand|park|shop|colony|nagar|area|house|store|mall|place|junction|cross|village|city|bazaar))\b/i)
    if (mLoc) placeAddress = mLoc[0]
  }

  // 5. Complainant
  const complainantName = getFirstVal(comp.name, firData?.complainant_name, firData?.complainantName, existingForm?.complainantName)
  const fatherHusbandName = getFirstVal(comp.father_husband_name, firData?.fatherHusbandName, existingForm?.fatherHusbandName)
  const dob = getFirstVal(comp.date_year_of_birth, firData?.dob, existingForm?.dob)
  const nationality = getFirstVal(comp.nationality, firData?.nationality, existingForm?.nationality) || 'Indian'
  const passportNo = getFirstVal(comp.passport_no, firData?.passportNo, existingForm?.passportNo)
  const passportDate = getFirstVal(comp.passport_date_of_issue, firData?.passportDate, existingForm?.passportDate)
  const passportPlace = getFirstVal(comp.passport_place_of_issue, firData?.passportPlace, existingForm?.passportPlace)
  const occupation = getFirstVal(comp.occupation, firData?.occupation, existingForm?.occupation)
  const complainantAddress = getFirstVal(comp.address, firData?.complainantAddress, existingForm?.complainantAddress)

  // 6. Accused details
  let accusedDetails = getFirstVal(
    firData?.accused_details,
    firData?.accusedDetails,
    firData?.accused,
    existingForm?.accusedDetails
  )
  if (!accusedDetails && incidentText) {
    const lowerInc = incidentText.toLowerCase()
    if (lowerInc.includes('unknown man') || lowerInc.includes('unknown male')) {
      accusedDetails = 'Unknown male accused; identity not known at this stage.'
    } else if (lowerInc.includes('unknown woman') || lowerInc.includes('unknown female')) {
      accusedDetails = 'Unknown female accused; identity not known at this stage.'
    } else if (lowerInc.includes('unknown')) {
      accusedDetails = 'Unknown accused person(s); identity not known at this stage.'
    }
  }

  // 7. Property details & value
  let propertyDetails = getFirstVal(
    firData?.property_details,
    firData?.propertyDetails,
    firData?.property,
    firData?.stolen_property,
    existingForm?.propertyDetails
  )
  let propertyValue = getFirstVal(
    firData?.property_value,
    firData?.propertyValue,
    firData?.estimated_value,
    firData?.value,
    existingForm?.propertyValue
  )

  if (!propertyValue && incidentText) {
    const mVal = incidentText.match(/(?:₹|rs\.?|rupees)\s*([\d,]+)/i)
    if (mVal) {
      propertyValue = `₹${mVal[1]}`
    }
  }

  // 8. FIR contents narrative
  const firContents = getFirstVal(
    firData?.fir_contents,
    firData?.firContents,
    firData?.narrative,
    firData?.statement,
    existingForm?.firContents,
    sanitizedIncident
  )

  // 9. Officer & Action
  const actionTaken = getFirstVal(firData?.action_taken, firData?.actionTaken, existingForm?.actionTaken) || 'Registered the case and took up the investigation'
  const officerRank = getFirstVal(officer.rank, firData?.officerRank, existingForm?.officerRank)
  const officerName = getFirstVal(officer.name, firData?.officerName, existingForm?.officerName)
  const officerNo = getFirstVal(officer.number, firData?.officerNo, existingForm?.officerNo)
  const dispatchDate = getFirstVal(dispatch.date, firData?.dispatchDate, existingForm?.dispatchDate)
  const dispatchTime = getFirstVal(dispatch.time, firData?.dispatchTime, existingForm?.dispatchTime)

  const actEntries = existingForm?.actEntries && existingForm.actEntries.length > 0
    ? existingForm.actEntries
    : [
        {
          act: 'Bharatiya Nyaya Sanhita, 2023',
          section: '',
          source: 'manual' as const,
        },
      ]

  return {
    district,
    policeStation,
    year,
    firNo,
    firDate,

    actEntries,
    act1: existingForm?.act1 || 'Bharatiya Nyaya Sanhita, 2023',
    section1: existingForm?.section1 || '',
    act2: existingForm?.act2 || '',
    section2: existingForm?.section2 || '',
    act3: existingForm?.act3 || '',
    section3: existingForm?.section3 || '',
    otherActs: existingForm?.otherActs || '',

    occurrenceDay,
    occurrenceDate,
    occurrenceTime,
    informationDate,
    informationTime,
    gdEntry,
    gdTime,

    informationType,

    placeDirection,
    beatNo,
    placeAddress,
    outsidePoliceStation,
    outsideDistrict,

    complainantName,
    fatherHusbandName,
    dob,
    nationality,
    passportNo,
    passportDate,
    passportPlace,
    occupation,
    complainantAddress,

    accusedDetails,
    delayReason: getFirstVal(firData?.delay_reason, firData?.delayReason, existingForm?.delayReason),
    propertyDetails,
    propertyValue,
    inquestDetails: getFirstVal(firData?.inquest_ud_case, firData?.inquestDetails, existingForm?.inquestDetails),
    firContents,

    actionTaken,
    officerRank,
    officerName,
    officerNo,

    dispatchDate,
    dispatchTime,
  }
}

export function extractSectionNumber(secStr: string): string {
  if (!secStr) return ''
  const match = secStr.match(/\b\d+[\w()]*\b/)
  return match ? match[0] : secStr.trim().toLowerCase()
}

export function deriveActEntries(
  currentEntries: ActSectionEntry[],
  suggestions: BnsSuggestion[]
): ActSectionEntry[] {
  const manualEntries = (currentEntries || []).filter(
    (entry) => entry.source === 'manual' && entry.section && entry.section.trim() !== ''
  )

  const acceptedSuggestions = (suggestions || []).filter(
    (sug) => sug.accepted && !sug.removed
  )

  const aiEntries: ActSectionEntry[] = acceptedSuggestions.map((sug) => {
    const formattedSection = sug.title
      ? `Section ${sug.section} — ${sug.title}`
      : `Section ${sug.section}`
    return {
      act: sug.act || 'Bharatiya Nyaya Sanhita, 2023',
      section: formattedSection,
      source: 'ai' as const,
    }
  })

  const aiSectionNums = new Set(aiEntries.map((e) => extractSectionNumber(e.section)))

  const nonDuplicateManual = manualEntries.filter(
    (e) => !aiSectionNums.has(extractSectionNumber(e.section))
  )

  if (aiEntries.length > 0 || nonDuplicateManual.length > 0) {
    return [...nonDuplicateManual, ...aiEntries]
  }

  return [
    {
      act: 'Bharatiya Nyaya Sanhita, 2023',
      section: '',
      source: 'manual' as const,
    },
  ]
}

export default function NewFIRPage() {
  const [statement, setStatement] = useState('')
  const [form, setForm] = useState<FormData>(initialForm)

  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [draftGenerated, setDraftGenerated] = useState(false)
  const [legalSuggestions, setLegalSuggestions] = useState<BnsSuggestion[]>([])
  const [legalAnalysisWarning, setLegalAnalysisWarning] = useState('')
  const [supportedSections, setSupportedSections] = useState<string[]>([])
  const [verifiedByOfficer, setVerifiedByOfficer] = useState(false)
  const [showRegenerateModal, setShowRegenerateModal] = useState(false)

  // Speech-to-text state
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(true)
  const [speechError, setSpeechError] = useState('')
  const recognitionRef = useRef<any>(null)

  const [saveStatus, setSaveStatus] = useState('')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognitionAPI =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (!SpeechRecognitionAPI) {
        setSpeechSupported(false)
      }

      const params = new URLSearchParams(window.location.search)
      const modeParam = params.get('mode')
      const draftIdParam = params.get('draft_id')

      // 1. NEW MODE: Explicit mode=new OR fresh navigation without mode/draft_id
      if (modeParam === 'new' || (!modeParam && !draftIdParam && sessionStorage.getItem('lawaid_fir_mode') !== 'resume')) {
        sessionStorage.removeItem('lawaid_fir_draft')
        sessionStorage.removeItem('lawaid_draft_id')
        localStorage.removeItem('lawaid_fir_draft')
        sessionStorage.setItem('lawaid_fir_mode', 'new')

        setStatement('')
        setForm(initialForm)
        setLegalSuggestions([])
        setLegalAnalysisWarning('')
        setSupportedSections([])
        setVerifiedByOfficer(false)
        setDraftGenerated(false)
        return
      }

      // 2. RESUME MODE: Explicit mode=resume OR draft_id parameter OR lawaid_fir_mode === 'resume'
      if (modeParam === 'resume' || draftIdParam || sessionStorage.getItem('lawaid_fir_mode') === 'resume') {
        const saved = sessionStorage.getItem('lawaid_fir_draft') || localStorage.getItem('lawaid_fir_draft')
        if (saved) {
          try {
            const parsed = JSON.parse(saved)
            setStatement(parsed.statement || '')
            setLegalSuggestions(parsed.legalSuggestions || [])
            setLegalAnalysisWarning(parsed.legalAnalysisWarning || '')
            setSupportedSections(parsed.supportedSections || [])
            setVerifiedByOfficer(!!parsed.verifiedByOfficer)

            const derivedEntries = deriveActEntries(parsed.actEntries || [], parsed.legalSuggestions || [])
            const syncedForm = getSynchronizedForm({
              ...parsed,
              actEntries: derivedEntries,
            })
            setForm((prev) => ({
              ...prev,
              ...syncedForm,
            }))
            setDraftGenerated(true)
            sessionStorage.setItem('lawaid_fir_mode', 'resume')
            return
          } catch (e) {
            console.error('Failed to parse saved draft:', e)
          }
        }
      }

      // 3. Fallback: Blank defaults
      sessionStorage.removeItem('lawaid_fir_draft')
      sessionStorage.removeItem('lawaid_draft_id')
      localStorage.removeItem('lawaid_fir_draft')
      sessionStorage.setItem('lawaid_fir_mode', 'new')
      setStatement('')
      setForm(initialForm)
      setLegalSuggestions([])
      setLegalAnalysisWarning('')
      setSupportedSections([])
      setVerifiedByOfficer(false)
      setDraftGenerated(false)
    }
  }, [])

  useEffect(() => {
    setForm((prev) => {
      const derived = deriveActEntries(prev.actEntries, legalSuggestions)
      const synced = getSynchronizedForm({
        ...prev,
        actEntries: derived,
      })
      if (JSON.stringify(prev) === JSON.stringify(synced)) {
        return prev
      }
      return synced
    })
  }, [legalSuggestions])

  function toggleListening() {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      setIsListening(false)
      return
    }

    if (typeof window === 'undefined') return
    const SpeechRecognitionAPI =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognitionAPI) {
      setSpeechError('Speech recognition is not supported by your browser. Please type the statement.')
      return
    }

    try {
      const recognition = new SpeechRecognitionAPI()
      recognition.continuous = true
      recognition.interimResults = false
      recognition.lang = 'en-IN'

      recognition.onstart = () => {
        setIsListening(true)
        setSpeechError('')
      }

      recognition.onresult = (event: any) => {
        let transcriptChunk = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            transcriptChunk += event.results[i][0].transcript
          }
        }
        if (transcriptChunk) {
          setStatement((prev) => (prev ? `${prev.trim()} ${transcriptChunk.trim()}` : transcriptChunk.trim()))
        }
      }

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition notice:', event.error)
        if (event.error === 'not-allowed') {
          setSpeechError('Microphone permission denied. Please allow microphone access.')
        }
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
      recognition.start()
    } catch (err) {
      console.error('Failed to start speech recognition:', err)
      setIsListening(false)
    }
  }

  function updateField(field: keyof FormData, value: string) {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  async function handleGenerateAiFir() {
    if (!statement.trim() || statement.trim().length < 10) {
      setAiError('Please enter at least 10 characters describing the incident statement.')
      return
    }

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop()
      setIsListening(false)
    }

    setAiLoading(true)
    setAiError('')

    try {
      const response = await policeAPI.generateFir(statement.trim())
      const resData = response.data

      if (resData && resData.fir_data) {
        const mappedForm = mapFirDataToFormData(resData.fir_data, resData.sanitized_incident || statement, form)
        setForm(mappedForm)
        setLegalSuggestions(resData.legal_suggestions || [])
        setLegalAnalysisWarning(resData.legal_analysis_warning || '')
        setSupportedSections(resData.supported_sections || [])
        setDraftGenerated(true)
        setVerifiedByOfficer(false)
      } else {
        setAiError('Unable to generate AI FIR draft. Please try again.')
      }
    } catch (err: any) {
      console.error('AI FIR Generation error:', err)
      setAiError(err?.response?.data?.detail || 'Error connecting to AI FIR generation service.')
    } finally {
      setAiLoading(false)
    }
  }

  function handleAcceptSuggestion(index: number) {
    setLegalSuggestions((prev) => {
      const updated = [...prev]
      if (updated[index]) {
        updated[index] = { ...updated[index], accepted: true, removed: false }
      }
      setForm((formPrev) =>
        getSynchronizedForm({
          ...formPrev,
          actEntries: deriveActEntries(formPrev.actEntries, updated),
        })
      )
      return updated
    })
  }

  function handleRemoveSuggestion(index: number) {
    setLegalSuggestions((prev) => {
      const updated = [...prev]
      if (updated[index]) {
        updated[index] = { ...updated[index], accepted: false, removed: true }
      }
      setForm((formPrev) =>
        getSynchronizedForm({
          ...formPrev,
          actEntries: deriveActEntries(formPrev.actEntries, updated),
        })
      )
      return updated
    })
  }

  function updateActEntry(index: number, field: 'act' | 'section', value: string) {
    setForm((prev) => {
      const updated = [...(prev.actEntries || [])]
      if (updated[index]) {
        updated[index] = {
          ...updated[index],
          [field]: value,
        }
      }
      return getSynchronizedForm({
        ...prev,
        actEntries: updated,
      })
    })
  }

  function addActEntry() {
    setForm((prev) =>
      getSynchronizedForm({
        ...prev,
        actEntries: [
          ...(prev.actEntries || []),
          {
            act: 'Bharatiya Nyaya Sanhita, 2023',
            section: '',
            source: 'manual',
          },
        ],
      })
    )
  }

  function removeActEntry(index: number) {
    setForm((prev) => {
      const target = (prev.actEntries || [])[index]
      if (target && target.source === 'ai') {
        const targetSecNum = extractSectionNumber(target.section)
        setLegalSuggestions((sugs) =>
          sugs.map((sug) =>
            extractSectionNumber(sug.section) === targetSecNum
              ? { ...sug, accepted: false, removed: true }
              : sug
          )
        )
      }
      const updated = (prev.actEntries || []).filter((_, i) => i !== index)
      return getSynchronizedForm({
        ...prev,
        actEntries: updated.length > 0 ? updated : [{ act: 'Bharatiya Nyaya Sanhita, 2023', section: '', source: 'manual' }],
      })
    })
  }

  function getSynchronizedForm(currentForm: FormData): FormData {
    const entries = currentForm.actEntries && currentForm.actEntries.length > 0 ? currentForm.actEntries : []
    const act1 = entries[0]?.act || 'Bharatiya Nyaya Sanhita, 2023'
    const section1 = entries[0]?.section || ''
    const act2 = entries[1]?.act || ''
    const section2 = entries[1]?.section || ''
    const act3 = entries[2]?.act || ''
    const section3 = entries[2]?.section || ''
    const otherActs = entries.length > 3
      ? entries.slice(3).map((e) => `${e.act} - ${e.section}`).filter((s) => s.trim() !== '-').join('; ')
      : ''

    return {
      ...currentForm,
      act1,
      section1,
      act2,
      section2,
      act3,
      section3,
      otherActs,
    }
  }

  async function saveDraft() {
    const syncedForm = getSynchronizedForm(form)
    const draftPayload = {
      ...syncedForm,
      statement,
      legalSuggestions,
      legalAnalysisWarning,
      supportedSections,
      verifiedByOfficer,
    }
    
    sessionStorage.setItem('lawaid_fir_mode', 'resume')
    sessionStorage.setItem('lawaid_fir_draft', JSON.stringify(draftPayload))
    
    try {
      const draftId = sessionStorage.getItem('lawaid_draft_id')
      if (draftId) {
        (draftPayload as any).draft_id = draftId
      }
      
      const res = await firDraftsAPI.saveDraft(draftPayload)
      if (res.data && res.data.draft_id) {
        sessionStorage.setItem('lawaid_draft_id', res.data.draft_id)
        setSaveStatus('Draft saved securely to backend!')
      } else {
        setSaveStatus('Draft saved locally (backend unavailable).')
      }
    } catch (e) {
      setSaveStatus('Draft saved locally (backend unavailable).')
    }
    
    setTimeout(() => setSaveStatus(''), 3000)
  }

  function generatePreview() {
    const syncedForm = getSynchronizedForm(form)
    sessionStorage.setItem('lawaid_fir_mode', 'resume')
    sessionStorage.setItem(
      'lawaid_fir_draft',
      JSON.stringify({
        ...syncedForm,
        statement,
        legalSuggestions,
        legalAnalysisWarning,
        supportedSections,
        verifiedByOfficer,
      })
    )
    window.location.href = '/police/new-fir/preview'
  }

  return (
    <>
      <Navbar />

      <main className="relative min-h-[calc(100vh-64px)] overflow-hidden text-[#12335B]">

        {/* Background */}
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-feature-bg.png"
            alt="LawAid legal background"
            className="h-full w-full object-cover object-center"
          />
        </div>

        {/* Light overlay */}
        <div className="fixed inset-0 -z-10 bg-[#f8f6f1]/10" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">

          {/* Page Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <span className="h-px w-10 bg-[#b98528]" />
              <span className="text-[11px] tracking-[0.3em] uppercase text-white font-medium">
                POLICE PORTAL
              </span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-[#cc8427] tracking-[-0.025em]">
                  AI-Assisted FIR Drafting
                </h1>
                <p className="mt-1.5 text-[#dca45a] text-sm md:text-base font-medium">
                  Prepare a First Information Report using the official IF1 format.
                </p>
              </div>

              <Link
                href="/police"
                className="self-start shrink-0 border border-[#d2a14b]/60 bg-[#b98528] hover:bg-[#9f7020] text-white px-5 py-2.5 rounded-full text-xs font-semibold transition shadow-sm"
              >
                ← Police Dashboard
              </Link>
            </div>
          </div>

          {/* STEP 1: STATEMENT INPUT WITH MICROPHONE & AI GENERATION TRIGGER */}
          <section className="bg-white/85 backdrop-blur-md rounded-[20px] p-6 sm:p-7 shadow-[0_15px_40px_rgba(18,51,91,0.10)] border border-white/80 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-xl font-bold text-[#12335B] flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#12335B] text-white text-xs font-bold">
                  1
                </span>
                Complainant / Incident Statement
              </h2>

              <button
                type="button"
                onClick={toggleListening}
                disabled={!speechSupported}
                className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold transition border ${
                  isListening
                    ? 'bg-red-100 text-red-700 border-red-300 animate-pulse'
                    : 'bg-[#f8f6f1] text-[#b98528] border-[#b98528]/40 hover:bg-white'
                } disabled:opacity-50`}
                title={speechSupported ? 'Click to dictate statement via microphone' : 'Speech recognition not supported in browser'}
              >
                {isListening ? (
                  <>
                    <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
                    Listening... (Click to Stop)
                  </>
                ) : (
                  <>
                    <span>🎙️</span>
                    Speak Statement
                  </>
                )}
              </button>
            </div>

            {speechError && (
              <p className="mb-3 text-xs text-amber-800 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                {speechError}
              </p>
            )}

            {/* Quick Sample Buttons */}
            <div className="mb-3">
              <p className="text-xs text-[#56718f] font-semibold mb-2">Sample Statements (Click to populate):</p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {SAMPLE_INCIDENTS.map((sample, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setStatement(sample.text)
                      setAiError('')
                    }}
                    className="text-xs bg-white border border-gray-300 hover:border-[#b98528] text-gray-700 px-3 py-1.5 rounded-lg whitespace-nowrap transition shadow-sm"
                  >
                    💡 {sample.title}
                  </button>
                ))}
              </div>
            </div>

            <textarea
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              rows={6}
              placeholder="Speak using the microphone button above or type/paste the raw complainant statement in detail. Include what happened, date/time, location, stolen property, or accused description..."
              className="w-full border border-gray-300 rounded-xl p-3.5 text-sm outline-none focus:ring-2 focus:ring-[#12335B] transition bg-white/90 leading-relaxed"
            />

            {aiError && (
              <p className="mt-3 text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-200 font-medium">
                {aiError}
              </p>
            )}

            <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-gray-100">
              <p className="text-xs text-[#56718f]">
                Speech transcript enters this text box. You can edit the text before generating the FIR.
              </p>

              <button
                type="button"
                onClick={handleGenerateAiFir}
                disabled={aiLoading || !statement.trim()}
                className="inline-flex items-center justify-center gap-2 bg-[#12335B] hover:bg-[#0d2949] text-white px-7 py-3 rounded-xl font-semibold text-sm transition shadow-md disabled:opacity-50"
              >
                {aiLoading ? (
                  <>
                    <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    Extracting Facts & Generating FIR...
                  </>
                ) : (
                  <>
                    ⚡ Generate AI FIR Draft
                  </>
                )}
              </button>
            </div>
          </section>

          {/* STEP 2: AI-SUGGESTED BNS PROVISIONS — OFFICER REVIEW REQUIRED */}
          {draftGenerated && (
            <section className="bg-white/95 backdrop-blur-md rounded-[20px] p-6 sm:p-7 shadow-[0_15px_40px_rgba(18,51,91,0.10)] border border-white/80 mb-8 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-200">
                <div>
                  <h2 className="font-serif text-xl font-bold text-[#12335B] flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#12335B] text-white text-xs font-bold">
                      2
                    </span>
                    AI-Suggested BNS Provisions — Officer Review Required
                  </h2>
                  <p className="text-xs text-gray-600 mt-1 font-medium">
                    Provisions identified by LawAid's grounded legal analysis. Review each suggestion and click <strong>[ Accept ]</strong> to populate it into the FIR Acts & Sections or <strong>[ Remove ]</strong> to discard.
                  </p>
                </div>

                <div className="shrink-0">
                  <span className="text-xs font-bold text-amber-900 bg-amber-100 px-3 py-1 rounded-full border border-amber-300">
                    AI-Suggested — Officer Review Required
                  </span>
                </div>
              </div>

              {/* Warning banner if legal analysis failed or had issues */}
              {legalAnalysisWarning && (
                <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 font-medium leading-relaxed flex items-start gap-3">
                  <span className="text-base shrink-0">⚠️</span>
                  <div>
                    <p className="font-bold">Automated Legal Analysis Notice</p>
                    <p className="mt-0.5">{legalAnalysisWarning}</p>
                  </div>
                </div>
              )}

              {/* Suggestion Cards */}
              {legalSuggestions.length > 0 ? (
                <div className="space-y-4">
                  {legalSuggestions.map((sug, idx) => (
                    <div
                      key={sug.id || idx}
                      className={`border rounded-xl p-5 transition-all shadow-sm ${
                        sug.accepted
                          ? 'bg-emerald-50/80 border-emerald-300'
                          : sug.removed
                          ? 'bg-gray-100/60 border-gray-200 opacity-60'
                          : 'bg-white border-amber-200 hover:border-amber-400'
                      }`}
                    >
                      {/* Card Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-100">
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-sm text-[#12335B] bg-[#12335B]/10 px-3 py-1 rounded-lg">
                            {sug.act} — Section {sug.section}
                          </span>
                          <span className="font-bold text-sm text-gray-900">{sug.title}</span>
                        </div>

                        <div className="flex items-center gap-2">
                          {sug.accepted ? (
                            <span className="text-xs font-bold text-emerald-800 bg-emerald-200 px-2.5 py-1 rounded-md border border-emerald-400">
                              ✓ Accepted into FIR
                            </span>
                          ) : sug.removed ? (
                            <span className="text-xs font-bold text-gray-600 bg-gray-200 px-2.5 py-1 rounded-md">
                              ✗ Removed
                            </span>
                          ) : (
                            <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2.5 py-1 rounded-md border border-amber-300">
                              {sug.status || 'Potentially Applicable BNS Provision — Officer Review Required'}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Card Body */}
                      {!sug.removed && (
                        <div className="mt-4 space-y-3 text-xs leading-relaxed text-gray-700">
                          {/* Why it may apply */}
                          <div>
                            <span className="font-bold text-[#12335B] block mb-0.5">Why this provision may apply:</span>
                            <p className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">{sug.why_it_may_apply}</p>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {/* Supporting Facts */}
                            {sug.supporting_facts && sug.supporting_facts.length > 0 && (
                              <div className="bg-emerald-50/50 p-3 rounded-lg border border-emerald-100">
                                <span className="font-bold text-emerald-900 block mb-1">Supporting facts from incident:</span>
                                <ul className="list-disc list-inside space-y-0.5 text-emerald-800">
                                  {sug.supporting_facts.map((fact, fIdx) => (
                                    <li key={fIdx}>{fact}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Uncertainty / Missing details */}
                            {sug.uncertainty && sug.uncertainty.length > 0 && (
                              <div className="bg-amber-50/50 p-3 rounded-lg border border-amber-100">
                                <span className="font-bold text-amber-900 block mb-1">Uncertainty / Requires verification:</span>
                                <ul className="list-disc list-inside space-y-0.5 text-amber-800">
                                  {sug.uncertainty.map((unc, uIdx) => (
                                    <li key={uIdx}>{unc}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>

                          {/* Punishment & Grounding Source */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-gray-100 text-[11px] text-gray-500">
                            <div>
                              <span className="font-bold text-gray-700">Statutory Punishment: </span>
                              <span>{sug.punishment}</span>
                            </div>
                            <div>
                              <span className="font-bold text-gray-700">Source: </span>
                              <span className="bg-gray-100 px-2 py-0.5 rounded text-gray-600 font-mono">{sug.grounding_source}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Card Action Controls */}
                      <div className="mt-4 flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                        {sug.accepted ? (
                          <button
                            type="button"
                            onClick={() => handleRemoveSuggestion(idx)}
                            className="px-3.5 py-1.5 rounded-lg border border-red-300 text-red-700 hover:bg-red-50 text-xs font-semibold transition"
                          >
                            Remove from FIR
                          </button>
                        ) : sug.removed ? (
                          <button
                            type="button"
                            onClick={() => handleAcceptSuggestion(idx)}
                            className="px-3.5 py-1.5 rounded-lg bg-[#12335B] text-white hover:bg-[#0d2949] text-xs font-semibold transition"
                          >
                            Re-accept Provision
                          </button>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => handleRemoveSuggestion(idx)}
                              className="px-4 py-2 rounded-xl border border-gray-300 text-gray-700 hover:bg-gray-100 text-xs font-semibold transition"
                            >
                              [ Remove ]
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAcceptSuggestion(idx)}
                              className="px-5 py-2 rounded-xl bg-emerald-700 text-white hover:bg-emerald-800 text-xs font-bold transition shadow-sm flex items-center gap-1.5"
                            >
                              <span>✓</span> [ Accept ]
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                !legalAnalysisWarning && (
                  <p className="text-xs text-gray-500 italic bg-gray-50 p-4 rounded-xl text-center border border-gray-200">
                    No automated BNS provisions suggested for this incident. You can manually add Acts & Sections using the <strong>+ Add Act / Section</strong> button in the form below.
                  </p>
                )
              )}
            </section>
          )}

          {/* STEP 3: OFFICIAL DIGITAL FIR TEMPLATE VIEW (EDITABLE) */}
          <div className="space-y-6">

            <div className="bg-[#fcfbfa] border-2 border-[#12335B]/30 rounded-[20px] p-6 sm:p-8 shadow-xl space-y-7">

              {/* Template Official Header */}
              <div className="text-center pb-6 border-b-2 border-[#12335B]/20">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#12335B] text-[#b98528] font-bold text-xl mb-2">
                  ⚖️
                </div>
                <h2 className="font-serif text-2xl font-bold text-[#12335B] tracking-tight uppercase">
                  FORM F.I.R. (IF1)
                </h2>
                <h3 className="text-xs font-bold text-[#b98528] tracking-wider uppercase mt-0.5">
                  FIRST INFORMATION REPORT (Under Section 173 BNSS 2023)
                </h3>

                {verifiedByOfficer ? (
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs font-bold shadow-sm mt-2.5">
                    <span>✓</span> Officer Verified
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-300 text-amber-900 text-xs font-medium shadow-sm mt-2.5">
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    <span className="font-bold">AI-Generated Draft</span>
                    <span className="text-gray-300">|</span>
                    <span>Review and edit the details before verification.</span>
                  </div>
                )}
              </div>

              {/* 1. FIR Identification */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-3">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5">
                  1. FIR Identification
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">District</label>
                    <input
                      type="text"
                      value={form.district}
                      onChange={(e) => updateField('district', e.target.value)}
                      placeholder="District"
                      className="w-full border rounded-md p-2 text-xs outline-none focus:ring-1 focus:ring-[#12335B] font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Police Station</label>
                    <input
                      type="text"
                      value={form.policeStation}
                      onChange={(e) => updateField('policeStation', e.target.value)}
                      placeholder="Police Station"
                      className="w-full border rounded-md p-2 text-xs outline-none focus:ring-1 focus:ring-[#12335B] font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Year</label>
                    <input
                      type="text"
                      value={form.year}
                      onChange={(e) => updateField('year', e.target.value)}
                      placeholder="Year"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">F.I.R. No.</label>
                    <input
                      type="text"
                      value={form.firNo}
                      onChange={(e) => updateField('firNo', e.target.value)}
                      placeholder="FIR No."
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium text-[#12335B]"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Date</label>
                    <input
                      type="text"
                      value={form.firDate}
                      onChange={(e) => updateField('firDate', e.target.value)}
                      placeholder="DD/MM/YYYY"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                </div>
              </div>

              {/* 2. Acts and Sections (Dynamic Entries) */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-4">
                <div className="flex items-center justify-between border-b pb-1.5">
                  <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider">
                    2. Acts & Sections (Grounded BNS 2023 Provisions)
                  </h4>
                  <span className="text-[10px] text-gray-500 font-medium">
                    {form.actEntries?.length || 0} {form.actEntries?.length === 1 ? 'Entry' : 'Entries'}
                  </span>
                </div>

                <div className="space-y-3">
                  {(form.actEntries || []).map((entry, idx) => (
                    <div key={idx} className="bg-gray-50/80 border border-gray-200 rounded-lg p-3 relative group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-[#12335B] uppercase tracking-wider">
                            Entry ({idx + 1})
                          </span>
                          {entry.source === 'ai' ? (
                            <span className="text-[9px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-medium">
                              AI Suggested
                            </span>
                          ) : (
                            <span className="text-[9px] bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-medium">
                              Officer Added
                            </span>
                          )}
                        </div>

                        {(form.actEntries?.length || 0) > 1 && (
                          <button
                            type="button"
                            onClick={() => removeActEntry(idx)}
                            className="text-xs text-red-600 hover:text-red-800 font-semibold px-2 py-0.5 rounded hover:bg-red-50 transition"
                            title="Remove this entry"
                          >
                            🗑 Remove
                          </button>
                        )}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">
                            Act ({idx + 1})
                          </label>
                          <input
                            type="text"
                            value={entry.act}
                            onChange={(e) => updateActEntry(idx, 'act', e.target.value)}
                            placeholder="Bharatiya Nyaya Sanhita, 2023"
                            className="w-full border border-gray-300 rounded-md p-2 text-xs outline-none focus:ring-1 focus:ring-[#12335B] bg-white font-medium"
                          />
                        </div>

                        <div>
                          <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">
                            Section(s) ({idx + 1})
                          </label>
                          <input
                            type="text"
                            value={entry.section}
                            onChange={(e) => updateActEntry(idx, 'section', e.target.value)}
                            placeholder="Section e.g. 304 - Snatching"
                            className="w-full border border-gray-300 rounded-md p-2 text-xs outline-none focus:ring-1 focus:ring-[#12335B] bg-white font-bold text-[#12335B]"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-1">
                  <button
                    type="button"
                    onClick={addActEntry}
                    className="w-full sm:w-auto border border-dashed border-[#12335B]/50 bg-white hover:bg-[#12335B]/5 text-[#12335B] px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <span>+</span> Add Act / Section
                  </button>
                </div>
              </div>

              {/* 3. Occurrence of Offence */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-3">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5">
                  3. Occurrence of Offence
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Day of Occurrence</label>
                    <input
                      type="text"
                      value={form.occurrenceDay}
                      onChange={(e) => updateField('occurrenceDay', e.target.value)}
                      placeholder="Day (e.g. Monday)"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Date of Occurrence</label>
                    <input
                      type="text"
                      value={form.occurrenceDate}
                      onChange={(e) => updateField('occurrenceDate', e.target.value)}
                      placeholder="Date (DD/MM/YYYY)"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Time of Occurrence</label>
                    <input
                      type="text"
                      value={form.occurrenceTime}
                      onChange={(e) => updateField('occurrenceTime', e.target.value)}
                      placeholder="Time (e.g. 20:00)"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                </div>
              </div>

              {/* 4. Type of Information */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5 mb-3">
                  4. Type of Information
                </h4>
                <div className="flex gap-4 items-center">
                  <label className="flex items-center gap-2 text-xs font-semibold">
                    <input
                      type="radio"
                      name="infoType"
                      value="Written"
                      checked={form.informationType === 'Written'}
                      onChange={() => updateField('informationType', 'Written')}
                    />
                    Written
                  </label>
                  <label className="flex items-center gap-2 text-xs font-semibold">
                    <input
                      type="radio"
                      name="infoType"
                      value="Oral"
                      checked={form.informationType === 'Oral'}
                      onChange={() => updateField('informationType', 'Oral')}
                    />
                    Oral
                  </label>
                </div>
              </div>

              {/* 5. Place of Occurrence */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-3">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5">
                  5. Place of Occurrence
                </h4>
                <div>
                  <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Address / Location</label>
                  <input
                    type="text"
                    value={form.placeAddress}
                    onChange={(e) => updateField('placeAddress', e.target.value)}
                    placeholder="Place Address"
                    className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Direction & Distance from PS</label>
                    <input
                      type="text"
                      value={form.placeDirection}
                      onChange={(e) => updateField('placeDirection', e.target.value)}
                      placeholder="Direction & Distance"
                      className="w-full border rounded-md p-2 text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Beat No.</label>
                    <input
                      type="text"
                      value={form.beatNo}
                      onChange={(e) => updateField('beatNo', e.target.value)}
                      placeholder="Beat No."
                      className="w-full border rounded-md p-2 text-xs outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* 6. Complainant / Informant */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-3">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5">
                  6. Complainant / Informant Details
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Complainant Name</label>
                    <input
                      type="text"
                      value={form.complainantName}
                      onChange={(e) => updateField('complainantName', e.target.value)}
                      placeholder="Complainant Name"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Father / Husband Name</label>
                    <input
                      type="text"
                      value={form.fatherHusbandName}
                      onChange={(e) => updateField('fatherHusbandName', e.target.value)}
                      placeholder="Father / Husband Name"
                      className="w-full border rounded-md p-2 text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Nationality</label>
                    <input
                      type="text"
                      value={form.nationality}
                      onChange={(e) => updateField('nationality', e.target.value)}
                      placeholder="Nationality"
                      className="w-full border rounded-md p-2 text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Address</label>
                    <input
                      type="text"
                      value={form.complainantAddress}
                      onChange={(e) => updateField('complainantAddress', e.target.value)}
                      placeholder="Complainant Address"
                      className="w-full border rounded-md p-2 text-xs outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* 7. Accused Details */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5 mb-2">
                  7. Details of Known / Suspected / Unknown Accused
                </h4>
                <input
                  type="text"
                  value={form.accusedDetails}
                  onChange={(e) => updateField('accusedDetails', e.target.value)}
                  placeholder="Accused Details"
                  className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                />
              </div>

              {/* 8. Property Details & Value */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-3">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5">
                  8. Particulars of Property Stolen / Involved & Value
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Property Stolen / Involved</label>
                    <input
                      type="text"
                      value={form.propertyDetails}
                      onChange={(e) => updateField('propertyDetails', e.target.value)}
                      placeholder="Particulars of Property"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Total Estimated Value (₹)</label>
                    <input
                      type="text"
                      value={form.propertyValue}
                      onChange={(e) => updateField('propertyValue', e.target.value)}
                      placeholder="Estimated Value"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                </div>
              </div>

              {/* 12. F.I.R. Contents Narrative */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5 mb-2">
                  12. F.I.R. Contents Narrative (AI-Generated Statement Summary)
                </h4>
                <textarea
                  value={form.firContents}
                  onChange={(e) => updateField('firContents', e.target.value)}
                  rows={6}
                  placeholder="Full formal narrative of the First Information Report..."
                  className="w-full border rounded-lg p-3 text-xs outline-none leading-relaxed bg-white font-medium"
                />
              </div>

              {/* 13 & 15. Action Taken & Officer Details */}
              <div className="border border-gray-300 rounded-xl p-4 bg-white/90 space-y-3">
                <h4 className="text-xs font-bold text-[#12335B] uppercase tracking-wider border-b pb-1.5">
                  13 & 15. Action Taken & Officer Details
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Action Taken</label>
                    <input
                      type="text"
                      value={form.actionTaken}
                      onChange={(e) => updateField('actionTaken', e.target.value)}
                      placeholder="Action Taken"
                      className="w-full border rounded-md p-2 text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Officer Name</label>
                    <input
                      type="text"
                      value={form.officerName}
                      onChange={(e) => updateField('officerName', e.target.value)}
                      placeholder="Officer Name"
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Rank & Badge No.</label>
                    <input
                      type="text"
                      value={form.officerRank}
                      onChange={(e) => updateField('officerRank', e.target.value)}
                      placeholder="Rank / Badge No."
                      className="w-full border rounded-md p-2 text-xs outline-none font-medium"
                    />
                  </div>
                </div>
              </div>

            </div>

            {/* STEP 4: VERIFICATION & FINAL ACTION CONTROLS */}
            <section className="bg-white/85 backdrop-blur-md rounded-[20px] p-6 shadow-md border border-white/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <label className="flex items-center gap-3 cursor-pointer text-xs text-[#12335B] font-semibold">
                <input
                  type="checkbox"
                  checked={verifiedByOfficer}
                  onChange={(e) => setVerifiedByOfficer(e.target.checked)}
                  className="w-4 h-4 rounded text-[#12335B] focus:ring-[#12335B]"
                />
                <span>I confirm that I have reviewed, edited, and verified this FIR draft in accordance with BNSS Section 173.</span>
              </label>

              <div className="flex flex-wrap items-center gap-3 shrink-0">
                {saveStatus && (
                  <span className="text-xs text-emerald-600 font-semibold animate-pulse">
                    {saveStatus}
                  </span>
                )}

                {draftGenerated && (
                  <button
                    type="button"
                    onClick={() => setShowRegenerateModal(true)}
                    disabled={aiLoading || !statement.trim()}
                    className="px-4 py-2.5 rounded-xl border border-[#12335B] text-xs font-semibold text-[#12335B] hover:bg-[#12335B]/5 transition disabled:opacity-50"
                  >
                    Regenerate AI Draft
                  </button>
                )}

                <button
                  type="button"
                  onClick={saveDraft}
                  className="px-4 py-2.5 rounded-xl border border-[#12335B] text-xs font-semibold text-[#12335B] hover:bg-[#12335B]/5 transition"
                >
                  Save Draft
                </button>

                <button
                  type="button"
                  onClick={() => {
                    sessionStorage.removeItem('lawaid_fir_draft')
                    setForm(initialForm)
                    setStatement('')
                    setDraftGenerated(false)
                    setVerifiedByOfficer(false)
                  }}
                  className="px-4 py-2.5 rounded-xl border border-gray-300 text-xs font-semibold text-gray-600 hover:bg-gray-100 transition"
                >
                  Reset Form
                </button>

                <button
                  type="button"
                  onClick={generatePreview}
                  disabled={!verifiedByOfficer}
                  className="bg-[#12335B] hover:bg-[#0d2949] text-white px-6 py-2.5 rounded-xl text-xs font-semibold transition shadow-md disabled:opacity-50"
                >
                  Preview FIR →
                </button>
              </div>
            </section>

          </div>

        </div>
      </main>

      {/* REGENERATE CONFIRMATION MODAL */}
      {showRegenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-lg shrink-0">
                ⚠️
              </div>
              <div>
                <h3 className="text-base font-bold text-[#12335B]">
                  Regenerate AI Draft?
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Re-analyzing complainant statement
                </p>
              </div>
            </div>

            <p className="text-xs text-gray-700 leading-relaxed bg-gray-50 p-3 rounded-xl border border-gray-200">
              This will replace the current AI-generated FIR fields with a new draft based on the incident statement. Any manual changes to the current draft may be replaced.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowRegenerateModal(false)}
                className="px-4 py-2 rounded-xl border border-gray-300 text-xs font-semibold text-gray-700 hover:bg-gray-100 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowRegenerateModal(false)
                  handleGenerateAiFir()
                }}
                className="px-5 py-2 rounded-xl bg-[#12335B] hover:bg-[#0d2949] text-white text-xs font-semibold transition shadow-sm"
              >
                Regenerate
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}