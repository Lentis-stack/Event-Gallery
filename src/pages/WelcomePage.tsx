import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import FilmShell from '../components/FilmShell';

import EventBranding from '../components/EventBranding';
import NavigationButtons from '../components/NavigationButtons';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import { getActiveEventConfig } from '../services/eventBridge';

/**
 * Cinematic welcome / hero page.
 * Looping slideshow + overlays + event branding + HOST / GUEST choices.
 */
export default function WelcomePage() {
  const navigate = useNavigate();
  const eventConfig = getActiveEventConfig();

  const handleNavigate = (destination: 'host' | 'guest') => {
    if (destination === 'host') {
      navigate('/admin');
    } else {
      navigate('/guest');
    }
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="welcome">
          <header className="welcome__top">
            <span className="welcome__eyebrow">Welcome to the joining of 2 to become 1</span>
          </header>

          <div className="welcome__center">
            <EventBranding showPlatform as="h1" />
          </div>

          <div className="welcome__bottom">
            {/* Thank-you message shown ABOVE the buttons */}
            {eventConfig.welcomeMessage && (
              <motion.div 
                className="welcome__message-box"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, delay: 0.3 }}
              >
                <div className="welcome__message-inner">
                  {eventConfig.welcomeMessage}
                </div>
              </motion.div>
            )}

            <NavigationButtons onNavigate={handleNavigate} />
            <p className="welcome__hint">Choose how you'd like to join the experience</p>
          </div>
          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}
