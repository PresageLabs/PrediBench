import { Check, Loader2, Mail, MessageCircle, Send, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from './ui/button'

interface ContactModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ContactModal({ isOpen, onClose }: ContactModalProps) {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [showSuccessAnimation, setShowSuccessAnimation] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      // Reset form when modal closes
      setTimeout(() => {
        setSubmitted(false)
        setEmail('')
        setMessage('')
        setShowSuccessAnimation(false)
      }, 300)
    }
  }, [isOpen])

  useEffect(() => {
    // Prevent body scroll when modal is open
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          message,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit contact form')
      }

      setSubmitted(true)
      setShowSuccessAnimation(true)
      setTimeout(() => setShowSuccessAnimation(false), 2000)
    } catch (error) {
      console.error('Error submitting form:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div
          className="bg-card border border-border rounded-lg shadow-xl w-full max-w-md transform transition-all animate-in zoom-in-95 slide-in-from-bottom-3 duration-300"
          onClick={(e) => e.stopPropagation()}
          style={{
            animation: showSuccessAnimation ? 'pulse 0.5s ease-in-out' : undefined
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-primary/10">
                <MessageCircle className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Get in Touch</h2>
                <p className="text-sm text-muted-foreground">We'd love to hear from you</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md hover:bg-accent transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {submitted ? (
              <div className="text-center py-8">
                <div className="mb-4">
                  <div className={`mx-auto w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center transition-all duration-500 ${showSuccessAnimation ? 'scale-110' : 'scale-100'}`}>
                    <Check className={`w-6 h-6 text-green-600 dark:text-green-400 transition-all duration-700 ${showSuccessAnimation ? 'scale-125 rotate-12' : 'scale-100 rotate-0'}`} />
                  </div>
                </div>
                <h3 className={`text-lg font-medium mb-2 transition-all duration-500 ${showSuccessAnimation ? 'scale-105' : 'scale-100'}`}>Message Sent!</h3>
                <p className="text-sm text-muted-foreground mb-6">
                  Thank you for reaching out. We'll get back to you as soon as possible.
                </p>
                <div className="flex gap-3 justify-center">
                  <Button
                    onClick={() => {
                      setSubmitted(false)
                      setEmail('')
                      setMessage('')
                    }}
                    variant="outline"
                  >
                    Send Another
                  </Button>
                  <Button onClick={onClose}>
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="modal-email" className="block text-sm font-medium mb-2">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                      id="modal-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="w-full pl-10 pr-3 py-2 border border-input bg-background rounded-md text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="your@email.com"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="modal-message" className="block text-sm font-medium mb-2">
                    Message
                  </label>
                  <textarea
                    id="modal-message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    required
                    rows={4}
                    className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
                    placeholder="Tell us what's on your mind..."
                  />
                </div>
                <div className="flex gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={onClose}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 relative overflow-hidden transition-all duration-200"
                  >
                    <span className={`flex items-center justify-center transition-all duration-300 ${isSubmitting ? 'opacity-0 scale-50' : 'opacity-100 scale-100'}`}>
                      <Send className="w-4 h-4 mr-2" />
                      Send Message
                    </span>
                    {isSubmitting && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        <span>Sending...</span>
                      </div>
                    )}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export function FloatingContactButton({ onClick }: { onClick: () => void }) {
  const [isHovered, setIsHovered] = useState(false)
  const [isClicked, setIsClicked] = useState(false)

  const handleClick = () => {
    setIsClicked(true)
    setTimeout(() => setIsClicked(false), 300)
    onClick()
  }

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="fixed bottom-6 right-6 z-30 group"
      aria-label="Contact us"
    >
      <div className="relative">
        {/* Pulse animation */}
        <div className="absolute inset-0 rounded-full bg-primary animate-ping opacity-25" />

        {/* Main button */}
        <div
          className={`relative flex items-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-full shadow-lg hover:shadow-xl transform transition-all duration-200 hover:scale-105 ${isClicked ? 'scale-95' : ''}`}
        >
          <MessageCircle className={`w-5 h-5 transition-transform duration-200 ${isClicked ? 'rotate-12 scale-110' : ''}`} />
          <span className={`font-medium transition-all duration-300 ${isHovered ? 'max-w-[100px] opacity-100' : 'max-w-0 opacity-0'} overflow-hidden whitespace-nowrap`}>
            Contact
          </span>
        </div>

        {/* Click ripple effect */}
        {isClicked && (
          <div className="absolute inset-0 rounded-full animate-ping bg-primary/30" />
        )}
      </div>
    </button>
  )
}