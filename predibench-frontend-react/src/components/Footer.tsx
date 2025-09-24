
interface FooterProps {
  onContactClick?: () => void
}

export function Footer({ onContactClick }: FooterProps) {
  const links = [
    { name: 'About', href: '/#About' },
    { name: 'Leaderboard', href: '/leaderboard' },
    { name: 'Models', href: '/models' },
    { name: 'Events', href: '/events' },
    { name: 'Contact', href: '#', onClick: onContactClick },
  ]

  return (
    <footer className="mt-auto border-t border-border bg-background">
      <div className="container mx-auto px-6 py-6">
        <div className="flex flex-col items-center space-y-4">
          <nav className="flex items-center space-x-8">
            {links.map((link, index) => (
              <a
                key={index}
                href={link.href}
                onClick={link.onClick ? (e) => { e.preventDefault(); link.onClick!(); } : undefined}
                className={`text-sm font-medium transition-colors cursor-pointer ${link.name === 'Contact'
                    ? 'text-blue-500 hover:text-blue-600'
                    : 'text-muted-foreground hover:text-foreground'
                  }`}
              >
                {link.name}
              </a>
            ))}
          </nav>

          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <a href="https://clairvoyance-ai.co/" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors">© 2025 Presage Labs</a>
            <div className="flex items-center space-x-3">
              <a
                aria-label="github link"
                href="https://github.com/clairvoyance-tech/PrediBench"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <div className="w-6 h-6">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 4.6499C7.85775 4.6499 4.5 8.0129 4.5 12.1627C4.5 15.4814 6.64875 18.2977 9.62925 19.2907C10.0042 19.3597 10.1407 19.1279 10.1407 18.9284C10.1407 18.7507 10.1348 18.2774 10.131 17.6512C8.0445 18.1049 7.60425 16.6439 7.60425 16.6439C7.26375 15.7754 6.77175 15.5444 6.77175 15.5444C6.09075 15.0794 6.8235 15.0884 6.8235 15.0884C7.57575 15.1409 7.97175 15.8624 7.97175 15.8624C8.64075 17.0099 9.7275 16.6784 10.1542 16.4864C10.2232 16.0012 10.4167 15.6704 10.6313 15.4829C8.96625 15.2932 7.215 14.6482 7.215 11.7697C7.215 10.9499 7.5075 10.2787 7.98675 9.75365C7.9095 9.5639 7.65225 8.79965 8.06025 7.76615C8.06025 7.76615 8.69025 7.56365 10.1227 8.53565C10.7346 8.36879 11.3658 8.2838 12 8.2829C12.6375 8.2859 13.2787 8.36915 13.878 8.53565C15.3097 7.56365 15.9382 7.7654 15.9382 7.7654C16.3477 8.79965 16.0898 9.5639 16.0133 9.75365C16.4932 10.2787 16.7843 10.9499 16.7843 11.7697C16.7843 14.6557 15.03 15.2909 13.3597 15.4769C13.629 15.7087 13.8682 16.1669 13.8682 16.8682C13.8682 17.8717 13.8593 18.6824 13.8593 18.9284C13.8593 19.1294 13.9943 19.3634 14.3752 19.2899C15.8687 18.789 17.167 17.8314 18.0866 16.5524C19.0062 15.2735 19.5006 13.7379 19.5 12.1627C19.5 8.0129 16.1415 4.6499 12 4.6499Z" fill="currentColor" />
                  </svg>
                </div>
              </a>
              <a
                aria-label="x link"
                href="https://x.com/predibench"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <div className="w-6 h-6">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M13.3021 10.8029L17.5685 5.84351L17.7862 5.59053H17.4524H16.4233H16.353L16.3072 5.64379L12.6657 9.87668L9.76624 5.65694L9.72061 5.59053H9.64004H6.16602H5.87501L6.03981 5.83037L10.5278 12.362L6.04994 17.5668L5.83228 17.8198H6.16602H7.19527H7.26553L7.31135 17.7666L11.1641 13.288L14.2325 17.7534L14.2781 17.8198H14.3587H17.8327H18.1237L17.9589 17.58L13.3021 10.8029ZM14.9226 16.774L11.8527 12.3829V12.3826L11.8251 12.3431L11.3636 11.6831L11.3636 11.683L7.86001 6.67158H9.06721L11.9848 10.845L11.9848 10.845L12.4463 11.5051L12.4463 11.5051L16.1299 16.774H14.9226Z" fill="currentColor" stroke="currentColor" strokeWidth="0.30625" />
                  </svg>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
