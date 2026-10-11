"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { authAPI } from "@/lib/api"
import { completeLogin, restoreSession, ROLE_ROUTES } from "@/lib/auth"

const ROLES = ["Citizen", "Police", "Lawyer"]

// Post-login destination: honour a `?next=` deep link only when it is a
// same-origin path inside the authenticated user's own role area.
function destinationFor(role: string): string {
  const home = ROLE_ROUTES[role.toLowerCase()] || "/"
  if (typeof window === "undefined") return home
  const next = new URLSearchParams(window.location.search).get("next")
  if (next && next.startsWith("/") && !next.startsWith("//") && home !== "/" &&
      (next === home || next.startsWith(`${home}/`) || next.startsWith(`${home}?`))) {
    return next
  }
  return home
}

export default function LoginPage() {
  const router = useRouter()
  const [role, setRole] = useState("Citizen")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      const user = await restoreSession()
      if (user) {
        router.replace(destinationFor(user.role))
      }
    }
    checkAuth()
  }, [router])

  // Modes: "login" | "forgot" | "reset"
  const [mode, setMode] = useState<"login" | "forgot" | "reset">("login")
  
  // For Reset mode
  const [resetToken, setResetToken] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  async function handleLogin() {
    setLoading(true)
    setError("")
    setMessage("")
    try {
      const res = await authAPI.login(email, password, role)
      const user = await completeLogin(res.data.access_token)
      router.push(destinationFor(user.role))
    } catch (err: any) {
      if (!err?.response) {
        setError("Cannot reach the LawAid server. Please check that the backend is running.")
      } else if (err.response.status === 401) {
        setError("Invalid email or password. Please try again.")
      } else if (err?.response?.status === 403) {
        setError(err.response.data.detail || "You do not have access to this portal.")
      } else if (err?.response?.status === 422) {
        setError("Something is missing from the request - check role/email/password.")
      } else {
        setError("Something went wrong. Please try again.")
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotPassword() {
    setLoading(true)
    setError("")
    setMessage("")
    try {
      const res = await authAPI.forgotPassword(email)
      setMessage(res.data.message)
    } catch (err: any) {
      setError(err.message || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  async function handleResetPassword() {
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match")
      return
    }
    setLoading(true)
    setError("")
    setMessage("")
    try {
      await authAPI.resetPassword(resetToken, newPassword)
      
      setMessage("Password updated successfully! Returning to login...")
      setTimeout(() => {
        setMode("login")
        setPassword("")
        setNewPassword("")
        setConfirmPassword("")
        setMessage("")
      }, 2000)
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0" >
        <img
          src="/images/lawaid-register.png"
          alt="LawAid legal background"
          className="h-full w-full object-cover object-center"
        />
      </div>
      <div className="absolute inset-0 bg-white/10" />

      <div className="absolute top-8 left-8 sm:top-10 sm:left-12 z-20">
        <div className="flex flex-col leading-none">
          <span className="font-serif text-[38px] sm:text-[42px] tracking-[-0.04em] text-[#12335B]">
            Law<span className="text-[#b98528]">Aid</span>
          </span>
          <span className="mt-1 text-[6px] sm:text-[7px] tracking-[0.22em] uppercase text-[#56718f]">
            KNOW • UNDERSTAND • GET HELP
          </span>
        </div>
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center px-5 py-8">
        <div className="w-full max-w-[500px] bg-white/85 backdrop-blur-[4px] border border-white/80 rounded-[26px] px-10 py-7 sm:px-12 sm:py-8 shadow-[0_20px_60px_rgba(18,51,91,0.12)]">

          <h2 className="font-serif text-[42px] sm:text-[46px] leading-tight tracking-[-0.025em] text-[#12335B] mb-7">
            {mode === "login" ? "Welcome Back" : mode === "forgot" ? "Reset Password" : "New Password"}
          </h2>

          {mode === "login" && (
            <div className="flex gap-2.5 mb-7">
              {ROLES.map(r => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  className={`flex-1 py-3 rounded-xl text-[17px] font-semibold border transition-all duration-200 ${
                    role === r
                      ? "bg-[#1d5da5] text-white border-[#1d5da5] shadow-sm"
                      : "bg-white/70 text-[#56718f] border-[#cbd5e1] hover:bg-white hover:border-[#b98528] hover:text-[#12335B] hover:shadow-sm"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-5">
            
            {(mode === "login" || mode === "forgot") && (
              <div>
                <label className="text-[17px] font-semibold text-[#12335B]">Email Address</label>
                <input
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  type="email"
                  className="w-full border border-[#cbd5e1] rounded-xl px-5 py-3.5 mt-2 text-[17px] text-[#12335B] bg-white/80 placeholder:text-[#9aa7b8] focus:ring-2 focus:ring-[#1d5da5]/30 focus:border-[#1d5da5] outline-none"
                />
              </div>
            )}

            {mode === "login" && (
              <div>
                <div className="flex justify-between items-center">
                  <label className="text-[17px] font-semibold text-[#12335B]">Password</label>
                  <button 
                    onClick={() => { setMode("forgot"); setError(""); setMessage(""); }}
                    className="text-sm font-semibold text-[#1d5da5] hover:underline"
                  >
                    Forgot Password?
                  </button>
                </div>
                <input
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  type="password"
                  className="w-full border border-[#cbd5e1] rounded-xl px-5 py-3.5 mt-2 text-[17px] text-[#12335B] bg-white/80 placeholder:text-[#9aa7b8] focus:ring-2 focus:ring-[#1d5da5]/30 focus:border-[#1d5da5] outline-none"
                />
              </div>
            )}

            {mode === "reset" && (
              <>
                <div>
                  <label className="text-[17px] font-semibold text-[#12335B]">New Password</label>
                  <input
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    type="password"
                    placeholder="••••••••"
                    className="w-full border border-[#cbd5e1] rounded-xl px-5 py-3.5 mt-2 text-[17px] text-[#12335B] bg-white/80 placeholder:text-[#9aa7b8] outline-none"
                  />
                </div>
                <div>
                  <label className="text-[17px] font-semibold text-[#12335B]">Confirm Password</label>
                  <input
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    type="password"
                    placeholder="••••••••"
                    className="w-full border border-[#cbd5e1] rounded-xl px-5 py-3.5 mt-2 text-[17px] text-[#12335B] bg-white/80 placeholder:text-[#9aa7b8] outline-none"
                  />
                </div>
              </>
            )}

            {error && <p className="text-red-500 text-sm font-medium">{error}</p>}
            {message && <p className="text-green-600 text-sm font-medium">{message}</p>}

            {mode === "login" && (
              <>
                <button
                  onClick={handleLogin}
                  disabled={loading}
                  className="w-full bg-[#c18a25] text-white py-3.5 rounded-xl text-[17px] font-bold hover:bg-[#ad781b] transition disabled:opacity-60"
                >
                  {loading ? "Logging in..." : "Login ?"}
                </button>
                <button
                  onClick={() => router.push("/register")}
                  className="w-full border border-[#12335B] text-[#12335B] py-3.5 rounded-xl text-[17px] font-semibold bg-white/20 hover:bg-white/50 transition"
                >
                  Register New Account
                </button>
              </>
            )}

            {mode === "forgot" && (
              <>
                <button
                  onClick={handleForgotPassword}
                  disabled={loading}
                  className="w-full bg-[#1d5da5] text-white py-3.5 rounded-xl text-[17px] font-bold hover:bg-[#15467e] transition disabled:opacity-60"
                >
                  {loading ? "Sending..." : "Send Reset Link"}
                </button>
                <button
                  onClick={() => { setMode("login"); setError(""); setMessage(""); }}
                  className="w-full text-[#56718f] py-2 text-[15px] font-semibold hover:text-[#12335B] transition"
                >
                  Back to Login
                </button>
              </>
            )}

            {mode === "reset" && (
              <button
                onClick={handleResetPassword}
                disabled={loading}
                className="w-full bg-[#1d5da5] text-white py-3.5 rounded-xl text-[17px] font-bold hover:bg-[#15467e] transition disabled:opacity-60"
              >
                {loading ? "Updating..." : "Update Password"}
              </button>
            )}

          </div>
        </div>
      </div>
    </main>
  )
}

