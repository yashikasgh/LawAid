'use client'

import Navbar from '@/components/Navbar'
import LawyerSidebar from '@/components/LawyerSidebar'

export default function LawyerCaseLayout({ 
  children, 
  caseId 
}: { 
  children: React.ReactNode
  caseId: string | null 
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      
      <div className="flex flex-1 relative">
        <LawyerSidebar caseId={caseId} />
        
        <main className="flex-1 lg:ml-[260px] relative min-h-[calc(100vh-64px)] overflow-x-hidden">
          <div className="fixed inset-0 -z-10 bg-[#f7f4ec]">
            <img 
              src="/images/lawaid-citizen-dashboard.png" 
              alt="" 
              className="h-full w-full object-cover object-center" 
            />
          </div>
          <div className="fixed inset-0 -z-10 bg-[#f7f4ec]/85" />
          
          {children}
        </main>
      </div>
    </div>
  )
}
