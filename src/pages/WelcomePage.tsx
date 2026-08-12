import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import FilmShell from '../components/FilmShell';

import EventBranding from '../components/EventBranding';
import NavigationButtons from '../components/NavigationButtons';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import { eventConfig } from '../config/event';

/**
 * Cinematic welcome / hero page.
 * Looping slideshow + overlays + event branding + HOST / GUEST choices.
 */
export default function WelcomePage() {
  const navigate = useNavigate();

  const handleNavigate = (destination: 'host' | 'guest') => {
    if (destination === 'host') {
      navigate('/host');
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
            <NavigationButtons onNavigate={handleNavigate} />
            <p className="welcome__hint">Choose how you'd like to join the experience</p>

            {eventConfig.welcomeMessage && (
              <motion.div 
                className="welcome__message-box"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, delay: 0.8 }}
              >
                <div className="welcome__message-inner">
                  {eventConfig.welcomeMessage}
                </div>
              </motion.div>
            )}
          </div>
          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}

