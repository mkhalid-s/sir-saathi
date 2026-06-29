export type StateCapability = 'guidance_only' | 'official_link_search' | 'pilot_indexed_search' | 'validated_indexed_search';

export interface StateSummary {
  stateId: string;
  name: string;
  languages: string[];
  capability: StateCapability;
  status: string;
  enumerationEnd?: string;
  claimsEnd?: string;
  finalRollDate?: string;
  officialLink: string;
}

export const states: StateSummary[] = [
  {
    stateId: 'IN-MH',
    name: 'Maharashtra',
    languages: ['Marathi', 'Hindi', 'English'],
    capability: 'pilot_indexed_search',
    status: 'Enumeration scheduled',
    enumerationEnd: '2026-07-29',
    claimsEnd: '2026-09-04',
    finalRollDate: '2026-10-07',
    officialLink: 'https://voters.eci.gov.in/'
  },
  {
    stateId: 'IN-WB',
    name: 'West Bengal',
    languages: ['Bengali', 'Hindi', 'English'],
    capability: 'guidance_only',
    status: 'Final roll published',
    finalRollDate: '2026-02-28',
    officialLink: 'https://ceowestbengal.wb.gov.in/SIR'
  }
];
