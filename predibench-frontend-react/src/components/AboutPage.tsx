export function AboutPage() {
  return (
    <div className="container mx-auto px-6 py-12 max-w-4xl">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">About PrediBench</h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            A comprehensive benchmark for evaluating large language models' prediction capabilities
          </p>
        </div>

        {/* Coming Soon Section */}
        <div className="bg-card border border-border rounded-lg p-8 text-center space-y-4">
          <div className="text-6xl mb-4">🚧</div>
          <h2 className="text-2xl font-semibold">Technical Blog Coming Soon</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            We're working on a comprehensive technical blog that will explain how we built PrediBench, 
            our methodology, challenges we faced, and the technical decisions behind the benchmark.
          </p>
        </div>

        {/* Evaluation Metrics Section */}
        <div className="bg-card border border-border rounded-lg p-8 space-y-6">
          <h2 className="text-2xl font-semibold text-center">Evaluation Metrics</h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-primary">Cumulative Profit & Loss (PnL)</h3>
              <p className="text-muted-foreground text-sm">
                Measures the financial performance of each model's predictions by tracking the cumulative 
                profit or loss from all trading positions. Higher values indicate better financial performance.
              </p>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-primary">Brier Score</h3>
              <p className="text-muted-foreground text-sm">
                A proper scoring rule that measures the accuracy of probabilistic predictions. 
                The original Brier score is calculated as the mean squared difference between predicted 
                probabilities and actual outcomes: <code className="bg-muted px-1 rounded text-xs">(prediction - outcome)²</code>
              </p>
              <p className="text-muted-foreground text-sm">
                <strong>In PrediBench:</strong> We display <code className="bg-muted px-1 rounded text-xs">1 - Brier Score</code> 
                so that higher values indicate better prediction accuracy, making it consistent with other metrics 
                where higher is better. Perfect predictions score 1.0, while random guessing scores around 0.75.
              </p>
            </div>
          </div>
        </div>

        {/* Preview Content */}
        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">What You'll Learn</h3>
            <ul className="space-y-2 text-muted-foreground">
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>How we designed the benchmark evaluation system</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>Technical architecture and infrastructure choices</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>Data collection and validation methodologies</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>Challenges in evaluating prediction accuracy</span>
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            <h3 className="text-xl font-semibold">Topics We'll Cover</h3>
            <ul className="space-y-2 text-muted-foreground">
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>LLM integration and API design</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>Real-time data processing and scoring</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>Frontend architecture and visualization</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-foreground mt-1">•</span>
                <span>Lessons learned and future improvements</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Stay Updated Section */}
        <div className="bg-muted/50 rounded-lg p-6 text-center space-y-4">
          <h3 className="text-lg font-semibold">Stay Updated</h3>
          <p className="text-muted-foreground">
            Follow our progress and be the first to know when we publish our technical deep-dive.
          </p>
          <div className="text-sm text-muted-foreground">
            Check back soon for updates!
          </div>
        </div>
      </div>
    </div>
  )
}