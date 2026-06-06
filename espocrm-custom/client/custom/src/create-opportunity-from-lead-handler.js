define(['action-handler'], (Dep) => {

    return class extends Dep {

        initCreateOpportunityFromLead() {}

        isCreateOpportunityFromLeadVisible() {
            const status = this.view.model.get('status');

            return !['Converted', 'Dead', 'Recycled'].includes(status);
        }

        buildOpportunityName() {
            const model = this.view.model;

            const parts = [
                model.get('accountName'),
                model.get('name'),
                model.get('firstName'),
                [model.get('firstName'), model.get('lastName')].filter(Boolean).join(' '),
            ];

            for (const part of parts) {
                if (typeof part === 'string' && part.trim()) {
                    return part.trim();
                }
            }

            return 'Opportunita';
        }

        buildOpportunityData(attributes) {
            const model = this.view.model;
            const opportunityData = {...(attributes.Opportunity || attributes.opportunity || {})};

            opportunityData.name = this.buildOpportunityName();

            if (opportunityData.amount == null && model.get('opportunityAmount') != null) {
                opportunityData.amount = model.get('opportunityAmount');
            }

            if (!opportunityData.leadSource && model.get('source')) {
                opportunityData.leadSource = model.get('source');
            }

            if (!opportunityData.assignedUserId && model.get('assignedUserId')) {
                opportunityData.assignedUserId = model.get('assignedUserId');
            }

            if (!opportunityData.assignedUserName && model.get('assignedUserName')) {
                opportunityData.assignedUserName = model.get('assignedUserName');
            }

            return opportunityData;
        }

        showConvertError(xhr) {
            let message = this.view.translate('Error');

            if (xhr && xhr.responseJSON) {
                const data = xhr.responseJSON;

                if (data.messageTranslation) {
                    message = this.view.translate(
                        data.messageTranslation.label,
                        data.messageTranslation.scope || 'messages',
                        data.messageTranslation.data || {}
                    );
                } else if (data.message) {
                    message = data.message;
                }

                if (data.field) {
                    message += ' (' + data.field + ')';
                }
            }

            Espo.Ui.error(message);
        }

        async createOpportunityFromLead() {
            const buttonName = 'createOpportunityFromLead';

            const confirmed = await new Promise(resolve => {
                this.view.confirm({
                    message: 'Creare un\'Opportunita da questo Lead?',
                    confirmText: 'Converti',
                }, () => resolve(true));

                this.view.once('cancel', () => resolve(false));
            });

            if (!confirmed) {
                return;
            }

            this.view.disableMenuItem(buttonName);

            try {
                const attributes = await Espo.Ajax.postRequest('Lead/action/getConvertAttributes', {
                    id: this.view.model.id,
                });

                const opportunityData = this.buildOpportunityData(attributes);

                const response = await Espo.Ajax.postRequest('Lead/action/convert', {
                    id: this.view.model.id,
                    records: {
                        Opportunity: opportunityData,
                    },
                });

                Espo.Ui.success(this.view.translate('Converted', 'labels', 'Lead'));

                await this.view.model.fetch();

                const opportunityId = response?.createdOpportunityId || response?.Opportunity?.id;

                if (opportunityId) {
                    this.view.getRouter().navigate(
                        '#Opportunity/view/' + opportunityId,
                        {trigger: true}
                    );
                }
            } catch (xhr) {
                this.showConvertError(xhr);
            } finally {
                this.view.enableMenuItem(buttonName);
            }
        }
    };
});
