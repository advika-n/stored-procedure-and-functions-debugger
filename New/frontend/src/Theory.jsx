import { useState } from 'react'
import { THEORY_TOPICS } from './theoryTopics'

function Theory() {
  const [activeTopicId, setActiveTopicId] = useState(THEORY_TOPICS[0].id)
  const activeTopic = THEORY_TOPICS.find((topic) => topic.id === activeTopicId) ?? THEORY_TOPICS[0]
  const ActiveContent = activeTopic.Content

  return (
    <div className="theory-layout">
      <nav className="theory-nav">
        {THEORY_TOPICS.map((topic) => (
          <button
            key={topic.id}
            className={topic.id === activeTopicId ? 'theory-nav-item theory-nav-item-active' : 'theory-nav-item'}
            onClick={() => setActiveTopicId(topic.id)}
          >
            {topic.title}
          </button>
        ))}
      </nav>
      <article className="theory-content">
        <h2>{activeTopic.title}</h2>
        <ActiveContent />
      </article>
    </div>
  )
}

export default Theory
