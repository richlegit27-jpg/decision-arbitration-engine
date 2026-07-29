from pathlib import Path


path = Path(
    "templates/nova_landing_home.html"
)


text = path.read_text(
    encoding="utf-8"
)


old_start = (
    '            <div class="nova-system-grid">'
)

old_end = (
    '            </div>\n'
    '        </section>\n\n'
    '        <section id="workflow"'
)


start = text.index(old_start)

end = text.index(
    old_end,
    start
)


new_block = r'''            <div class="nova-system-grid">

                <article>
                    <div class="nova-icon">🧠</div>
                    <h3>Project Brain</h3>
                    <p>
                        Nova keeps goals, blockers, decisions, and direction
                        connected so complex work continues instead of resetting.
                    </p>
                </article>

                <article>
                    <div class="nova-icon">🧬</div>
                    <h3>Decision Memory</h3>
                    <p>
                        Nova learns from previous outcomes and uses history
                        to improve future decisions.
                    </p>
                </article>

                <article>
                    <div class="nova-icon">⚙️</div>
                    <h3>Execution Engine</h3>
                    <p>
                        Turn ideas into structured plans, tracked actions,
                        and measurable progress.
                    </p>
                </article>

                <article>
                    <div class="nova-icon">🗂️</div>
                    <h3>Persistent Sessions</h3>
                    <p>
                        Return to previous work with the same project context,
                        decisions, and history available.
                    </p>
                </article>

                <article>
                    <div class="nova-icon">📎</div>
                    <h3>File Intelligence</h3>
                    <p>
                        Work with uploads, documents, images, and project
                        material inside one connected workspace.
                    </p>
                </article>

                <article>
                    <div class="nova-icon">🛡️</div>
                    <h3>Operator Control</h3>
                    <p>
                        Keep ownership, system health, safety boundaries,
                        and important decisions visible.
                    </p>
                </article>

            </div>
        </section>

        <section id="workflow"'''


updated = (
    text[:start]
    + new_block
    + text[end + len('            </div>\n        </section>\n\n        <section id="workflow"'):]
)


path.write_text(
    updated,
    encoding="utf-8"
)


print(
    "Nova system section upgraded."
)