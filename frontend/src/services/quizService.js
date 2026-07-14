import api from '../config/api';

export const quizService = {
  generateQuiz: async ({ documentId, numMcqs = 10, numShortQuestions = 5, userId }) => {
    const payload = {
      document_id: documentId,
      num_mcqs: numMcqs,
      num_short_questions: numShortQuestions,
    };
    const parsed = parseInt(userId, 10);
    if (!Number.isNaN(parsed)) payload.user_id = parsed;
    const response = await api.post('/quiz/generate', payload, { timeout: 60000 });
    return response.data;
  },

  submitFull: async ({ mcqAnswers, mcqData, shortAnswers, shortData, userId, documentId, documentName, questionTimings }) => {
    const payload = {
      mcq_answers: mcqAnswers,
      mcq_data: mcqData,
      short_answers: shortAnswers,
      short_data: shortData,
    };
    const parsed = parseInt(userId, 10);
    if (!Number.isNaN(parsed)) payload.user_id = parsed;
    if (documentId) payload.document_id = documentId;
    if (documentName) payload.document_name = documentName;
    if (Array.isArray(questionTimings) && questionTimings.length > 0) {
      payload.question_timings = questionTimings;
    }
    const response = await api.post('/quiz/submit-full', payload);
    return response.data;
  },

  getHint: async ({ question, correctAnswer, concept, questionType }) => {
    const payload = { question, correct_answer: correctAnswer };
    if (concept) payload.concept = concept;
    if (questionType) payload.question_type = questionType;
    const response = await api.post('/quiz/hint', payload);
    return response.data;
  },

  logSupportEvent: async ({ userId, questionId, supportType, quizId }) => {
    const payload = { user_id: userId, question_id: questionId, support_type: supportType };
    if (quizId != null) payload.quiz_id = quizId;
    try {
      const response = await api.post('/quiz/support-log', payload);
      return response.data;
    } catch {
      // Non-critical — never block the UI for a tracking failure
      return null;
    }
  },
};
