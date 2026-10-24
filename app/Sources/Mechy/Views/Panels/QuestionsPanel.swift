import SwiftUI
import AppKit

/// Questions (questions/*.yaml) as numbered note boxes. Tap a choice (or type a
/// number / text, or pick an image) -> writes `answer`.
struct QuestionsPanel: View {
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        if session.questions.isEmpty {
            EmptySheet(symbol: "questionmark.bubble", label: "No questions")
        } else {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    let ordered = session.openQuestions + session.questions.filter(\.isAnswered)
                    ForEach(Array(ordered.enumerated()), id: \.element.id) { i, q in
                        QuestionCard(question: q, number: i + 1)
                        Hairline()
                    }
                }
            }
        }
    }
}

struct QuestionCard: View {
    let question: Question
    let number: Int
    @EnvironmentObject var session: ProjectSession
    @State private var draft = ""
    @State private var editing = false

    var body: some View {
        HStack(alignment: .top, spacing: Theme.Space.s) {
            NoteNumber(n: number, active: !question.isAnswered)
            VStack(alignment: .leading, spacing: Theme.Space.s) {
                Text(question.text)
                    .font(Theme.Typo.body)
                    .foregroundStyle(question.isAnswered ? Theme.muted : Theme.ink)
                    .fixedSize(horizontal: false, vertical: true)
                if let img = question.image {
                    FileThumb(url: session.url(img), contentMode: .fit)
                        .frame(maxWidth: .infinity, maxHeight: 120)
                        .overlay(Rectangle().stroke(Theme.hairline, lineWidth: 1))
                }
                if question.isAnswered && !editing {
                    HStack(spacing: Theme.Space.s) {
                        Text(question.answer ?? "").font(Theme.Typo.monoBody).foregroundStyle(Theme.ink)
                            .boxed(Theme.ink, padding: 2)
                        Button("Change") { editing = true }
                            .buttonStyle(.plain)
                            .monoLabel()
                    }
                } else {
                    input
                }
            }
        }
        .padding(Theme.Space.m)
        .opacity(question.isAnswered && !editing ? 0.75 : 1)
    }

    @ViewBuilder private var input: some View {
        switch question.kind {
        case .choice:
            WrapGrid(minWidth: 100) {
                ForEach(question.choices, id: \.self) { choice in
                    let selected = question.answer == choice
                    Button { submit(.string(choice)) } label: {
                        Text(choice)
                            .font(Theme.Typo.small)
                            .foregroundStyle(selected ? Theme.accent : Theme.ink)
                            .multilineTextAlignment(.leading)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal, Theme.Space.s)
                            .padding(.vertical, Theme.Space.xs + 2)
                            .overlay(Rectangle().stroke(selected ? Theme.accent : Theme.ink, lineWidth: 1))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
        case .number:
            HStack(spacing: Theme.Space.s) {
                TextField("0.0", text: $draft)
                    .textFieldStyle(.plain)
                    .font(Theme.Typo.number)
                    .frame(width: 100)
                    .padding(.horizontal, 6).padding(.vertical, 3)
                    .overlay(Rectangle().stroke(Theme.ink, lineWidth: 1))
                    .onSubmit(submitDraft)
                Button("Answer", action: submitDraft).buttonStyle(SheetButtonStyle(filled: true, compact: true))
                    .disabled(Double(draft.trimmingCharacters(in: .whitespaces)) == nil)
            }
        case .text:
            HStack(alignment: .bottom, spacing: Theme.Space.s) {
                TextField("Answer", text: $draft, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(Theme.Typo.small)
                    .lineLimit(1...4)
                    .padding(.horizontal, 6).padding(.vertical, 4)
                    .overlay(Rectangle().stroke(Theme.ink, lineWidth: 1))
                    .onSubmit(submitDraft)
                Button("Answer", action: submitDraft).buttonStyle(SheetButtonStyle(filled: true, compact: true))
                    .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        case .image:
            Button("Choose image") { pickImage() }.buttonStyle(SheetButtonStyle(compact: true))
        }
    }

    private func submitDraft() {
        let t = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        if question.kind == .number {
            guard let d = Double(t) else { return }
            submit(.number(d))
        } else {
            submit(.string(t))
        }
        draft = ""
    }

    private func submit(_ value: YAMLScalar) {
        session.answer(question, with: value)
        editing = false
    }

    private func pickImage() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.image]
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            session.answer(question, withImageAt: url)
            editing = false
        }
    }
}
